"""Adaptive AMD monthwise percentile selector (v3, October 2026).

The selector does NOT predict an unknown future market regime. It draws ONE
coherent modeled market-condition history (credit, regime, earnings beliefs and
psychology), then independently computes each month's conditional median price
across scenarios with comparable contemporaneous conditions. The chosen value
is ranked in that month's overall distribution and constrained to P10-P90.
This is not another stochastic price generator; no turning points are assigned
by calendar month and no extra independent volatility is added.

Optional monthly controls:
- market_condition: force the median price of paths currently in that regime.
- manual_percentile: 0=automatic; 10..90=the user-specified percentile.
These overrides are what-if experiments and DO NOT guarantee a coherent
single trading trajectory across months. Even automatic conditional medians are
not themselves a single actual simulation: the *underlying market-state
conditioning history* is joint and coherent, but prices are conditional
cross-sectional medians, separately selected each month.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd

LABELS={-2:'Severe panic',-1:'Risk-off',0:'Neutral',1:'Optimistic',2:'Euphoric'}
MARKET_OPTIONS=['Auto','Severe panic','Risk-off','Neutral','Optimistic','Euphoric']
MARKET_TO_VALUE={v:k for k,v in LABELS.items()}

@dataclass
class SelectorConfig:
    selector_seed:int=20261019
    path_index:int|None=None
    low_percentile:float=.10
    high_percentile:float=.90
    min_conditional_paths:int=12
    method:str='conditioned'  # conditioned (default), or path_rank
    condition_strength:float=1.0
    psyche_strength:float=.65

    def validate(self,n:int):
        if not isinstance(self.selector_seed,(int,np.integer)):raise ValueError('selector_seed must be an integer')
        if self.path_index is not None and not 0<=self.path_index<n:
            raise ValueError(f'path_index must be in [0,{n-1}]')
        if not (0.0<self.low_percentile<.5<self.high_percentile<1.0):
            raise ValueError('Need percentile limits spanning 50%, strictly within 0..100%')
        if self.min_conditional_paths<1:raise ValueError('min_conditional_paths must be positive')
        if self.method not in ('conditioned','path_rank'):
            raise ValueError('selector method must be conditioned or path_rank')
        if not (0<=self.condition_strength<=4 and 0<=self.psyche_strength<=2):
            raise ValueError('conditioning strengths are out of range')


def blank_overrides(months:list[str]|pd.Series)->pd.DataFrame:
    """A month-by-month override sheet. Zero percentile means automatic."""
    return pd.DataFrame({'month':list(months),'market_condition':'Auto',
                         'manual_percentile':0.0,'notes':''})


def _validated_overrides(overrides:pd.DataFrame|None,months:list[str])->pd.DataFrame:
    if overrides is None:
        return blank_overrides(months)
    required=['month','market_condition','manual_percentile']
    missing=set(required)-set(overrides.columns)
    if missing:raise ValueError('Missing selector-overrides columns: '+','.join(sorted(missing)))
    x=overrides.copy()
    if len(x)!=len(months) or x.month.tolist()!=months:
        raise ValueError('Selector override months must exactly match the 25 chart points (Oct 2026 through Oct 2028)')
    x.market_condition=x.market_condition.fillna('Auto')
    if not x.market_condition.isin(MARKET_OPTIONS).all():
        raise ValueError('market_condition must be Auto or a supported market regime')
    x.manual_percentile=pd.to_numeric(x.manual_percentile.fillna(0),errors='raise')
    chosen=(x.manual_percentile==0) | x.manual_percentile.between(10,90)
    if not chosen.all():raise ValueError('manual_percentile must be 0 (automatic) or 10–90')
    return x


def _midrank_percentile(ordered:np.ndarray,v:float)->float:
    left=np.searchsorted(ordered,v,side='left')
    right=np.searchsorted(ordered,v,side='right')
    # numpy.quantile(method='linear') uses index p*(n-1), not p*n.
    # Using the midpoint of tied observations keeps exact price/rank agreement
    # for uncapped paths, including under widely dispersed price distributions.
    if left==0 and right==len(ordered):
        return .5
    return float(((left+right-1)/2)/(len(ordered)-1))


def _weighted_median(values:np.ndarray,weights:np.ndarray)->float:
    ordered=np.argsort(values)
    v=values[ordered];w=weights[ordered]
    return float(v[min(len(v)-1,int(np.searchsorted(np.cumsum(w),w.sum()/2,side='left')))])


def _conditioned_market_price(result:dict,t:int,selected_path:int,desired_state:int,
                               strength:float,psyche_strength:float,
                               min_paths:int,explicit:bool)->tuple[float,int,float]:
    """Conditional price given a simulated market environment in month t.

    Exact market-type grouping plus kernel conditioning on *current* AI-credit
    stress, business scenario posterior and investor-psyche residual. No lookahead
    from later simulation months, no prechosen optimistic quarter, and no extra
    random price shock. The bandwidths are adjustable subjective assumptions.
    """
    vals=result['paths'][:,t]
    all_states=result['states'][:,t]
    active=(all_states==desired_state)
    count=int(active.sum())
    if count<min_paths:
        if explicit:
            raise ValueError(f'{result["monthly"].month.iloc[t]}: chosen regime has only {count} simulated paths. '
                             f'Increase n_paths, or choose a better-supported regime.')
        # A rare automatically simulated state still has a defined scenario.
        # Soft condition on regime distance rather than pretending there are
        # enough independent observations for an exact conditional median.
        state_weight=np.exp(-1.8*np.abs(all_states-desired_state))
    else:
        state_weight=active.astype(float)
    credit=result['credit'][:,t]
    bull=result['beliefs'][:,t,2]
    psy=result['sentiment_log_residual'][:,t]
    c0=credit[selected_path]
    b0=bull[selected_path]
    s0=psy[selected_path]
    credit_dist=((credit-c0)/.40)**2
    evidence_dist=((bull-b0)/.23)**2
    psyche_dist=((psy-s0)/.38)**2
    penalties=.5*strength*(credit_dist+evidence_dist+psyche_strength*psyche_dist)
    weights=state_weight*np.exp(-np.clip(penalties,0,50))
    if weights.sum()<1e-12:
        raise ValueError('Conditional market-state weights underflowed')
    n_eff=float(weights.sum()**2/(weights*weights).sum())
    return _weighted_median(vals,weights),count,n_eff


def _compute_original_selector(result:dict,config:SelectorConfig|None=None,
                           overrides:pd.DataFrame|None=None)->pd.DataFrame:
    """Choose one independently varying percentile per month inside P10-P90.

    The default percentile is the rank of the conditional median given ONE
    coherent future sequence of simulated market regimes, credit conditions,
    evidence-updated EPS beliefs, and sentiment residuals. We calculate this
    month-by-month from other simulations with similar conditions. The future
    sequence is unknown, so the seed chooses a hypothetical conditional state
    history, NOT the statistically most likely exact history.
    The alternative path_rank mode follows the exact price of the underlying
    jointly simulated trajectory (clipped to the selected P10-P90 band).
    """
    config=config or SelectorConfig()
    prices=result['paths']
    if prices.ndim!=2 or prices.shape[1]!=25:
        raise ValueError('Expected full simulation array with 25 monthly price columns')
    n=prices.shape[0]
    config.validate(n)
    months=result['monthly'].month.astype(str).tolist()
    controls=_validated_overrides(overrides,months)
    idx=(int(np.random.default_rng(config.selector_seed).integers(n))
         if config.path_index is None else int(config.path_index))
    selected=[]
    ref=result['monthly']
    for t,month in enumerate(months):
        ordered=np.sort(prices[:,t])
        row=controls.iloc[t]
        override_regime=row.market_condition
        manual=float(row.manual_percentile)
        effective_count=n
        if t==0:
            raw=float(prices[idx,0]);rank=.5;price=raw;source='Common scenario anchor'
            group_count=n
        elif manual>0:
            rank=manual/100
            raw=float(np.quantile(ordered,rank))
            source='User-specified percentile (scenario override)';group_count=n
        elif override_regime!='Auto':
            v=MARKET_TO_VALUE[override_regime]
            mask=result['states'][:,t]==v
            group_count=int(mask.sum())
            if group_count<config.min_conditional_paths:
                raise ValueError(f'{month}: {override_regime} has only {group_count} model paths; '
                                 f'need at least {config.min_conditional_paths}. '
                                 'Change the override or increase simulations.')
            raw,group_count,effective_count=_conditioned_market_price(
                result,t,idx,v,config.condition_strength,
                config.psyche_strength,config.min_conditional_paths,True)
            rank=_midrank_percentile(ordered,raw)
            source='Conditional price given manually selected market regime, credit and psyche'
        elif config.method=='path_rank':
            raw=float(prices[idx,t])
            rank=_midrank_percentile(ordered,raw)
            group_count=n
            source='Rank of one coherent simulated trading trajectory'
        else:
            desired=int(result['states'][idx,t])
            raw,group_count,effective_count=_conditioned_market_price(
                result,t,idx,desired,config.condition_strength,
                config.psyche_strength,config.min_conditional_paths,False)
            rank=_midrank_percentile(ordered,raw)
            source='Conditional price from market state, credit, earnings beliefs and psyche'
        p=float(np.clip(rank,config.low_percentile,config.high_percentile))
        price=float(np.quantile(ordered,p)) if t>0 else float(prices[idx,0])
        actual_regime=int(result['states'][idx,t])
        reported_regime=override_regime if override_regime!='Auto' else LABELS[actual_regime]
        credit=float(result['credit'][idx,t])
        bull=float(result['beliefs'][idx,t,2])
        bear=float(result['beliefs'][idx,t,0])
        pysche=float(result['sentiment_log_residual'][idx,t]) if 'sentiment_log_residual' in result else np.nan
        selected.append({'month':month,
            'smart_selected_price':round(price,2),
            'smart_percentile':round(p*100,2),
            'unbounded_rank_percentile':round(rank*100,2),
            'raw_joint_scenario_price':round(raw,2),
            'p10':float(ref.p10.iloc[t]),'p50':float(ref.green_integrated_median.iloc[t]),
            'p80':float(ref.orange_optimistic_p80.iloc[t]),'p90':float(ref.p90.iloc[t]),
            'market_type':reported_regime,
            'joint_scenario_market_type':LABELS[actual_regime],
            'credit_stress_index':round(credit,3),
            'subjective_p_acceleration':round(bull,4),
            'subjective_p_slowdown':round(bear,4),
            'trading_psychology_residual_log':round(pysche,4),
            'selector_source':source,
            'capped_to_p10_p90':bool(abs(p-rank)>1e-9),
            'selector_path_index':idx,
            'conditional_path_count':group_count,
            'effective_conditioned_sample':round(float(effective_count),1),
            'underlying_joint_scenario_price':round(float(prices[idx,t]),2)})
    df=pd.DataFrame(selected)
    df['selected_monthly_return_percent']=np.round(df.smart_selected_price.pct_change()*100,2)
    df.loc[0,'selected_monthly_return_percent']=0.0
    return df


def compute_smart_selector(result, config=None, overrides=None):
    """Original selector with scenario-JSON integration and export aliases."""
    if config is None:
        config = SelectorConfig(**result['config']['selector']) if 'config' in result else SelectorConfig()
    if overrides is None and 'config' in result:
        overrides = pd.DataFrame(result['config']['monthly_overrides'])
    elif isinstance(overrides, list):
        overrides = pd.DataFrame(overrides)
    output = _compute_original_selector(result, config, overrides)
    aliases = {'selected_price':'smart_selected_price', 'percentile':'smart_percentile',
               'raw_percentile':'unbounded_rank_percentile', 'raw_price':'raw_joint_scenario_price',
               'clipped':'capped_to_p10_p90', 'path_index':'selector_path_index',
               'market_regime':'market_type', 'credit_stress':'credit_stress_index',
               'acceleration_belief':'subjective_p_acceleration', 'sentiment':'trading_psychology_residual_log',
               'same_regime_count':'conditional_path_count', 'effective_sample_size':'effective_conditioned_sample'}
    for target, original in aliases.items():
        output[target] = output[original]
    output['method'] = config.method
    return output
