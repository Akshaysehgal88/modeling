"""AMD evidence-conditioned traded-price research model, version 3 with monthly smart selector (19 Oct 2026).

This is a TRANSPARENT CONDITIONAL SIMULATOR, not a fitted price prediction.
Prices = evolving earnings beliefs * a valuation reference * changes in market-pricing state.
A bearish state held constant does NOT automatically apply another bearish discount.
The optimistic/integrated chart lines are quantiles OF THE SAME JOINT distribution,
not cherry-picked sample paths with different market starting conditions.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / 'data'
MONTHS = pd.period_range('2026-11',periods=24,freq='M')
START = pd.Period('2026-10',freq='M')
START_DATE = '2026-10-16'
REGIMES=np.array([-2,-1,0,1,2],dtype=np.int8)
REGIME_LOG_PREMIUM=np.array([-.18,-.09,0,.10,.24],dtype=float)
SCENARIO_LABELS=['slowdown','reference','acceleration']
PRIOR=np.array([.25,.55,.20])  # subjective priors, not probabilities fitted from market
SCENARIO_EPS={
    'slowdown': {2026:7.72,2027:11.80,2028:15.50,2029:19.00,2030:24.00},
    'reference':{2026:7.72,2027:16.07,2028:23.48,2029:29.19,2030:42.37},
    'acceleration':{2026:7.72,2027:19.30,2028:33.72,2029:48.54,2030:64.85},
}

@dataclass
class Settings:
    spot:float=528.75
    n_paths:int=6000
    seed:int=20261018
    eps26:float=7.72
    eps27:float=16.07
    eps28:float=23.48
    eps29:float=29.19
    eps30:float=42.37
    stabilized_forward_pe:float=26.
    pe_normalization_months:float=24.
    initial_credit_stress:float=.90
    initial_regime:int=-1
    credit_persistence:float=.94
    credit_long_run:float=.65
    credit_monthly_noise:float=.14
    credit_price_sensitivity:float=.32
    evidence_strength:float=1.0
    scenario_discrimination:float=.20
    earnings_scenario_spread:float=1.0
    peer_shock_scale:float=.65
    idio_shock_scale:float=.60
    optimism_feedback:float=1.0
    pessimism_feedback:float=1.0
    momentum_feedback:float=.26
    switching_tendency:float=1.0
    sentiment_persistence:float=.82
    initial_lookthrough_weight:float=.16

    def earnings(self):
        return {2026:self.eps26,2027:self.eps27,2028:self.eps28,2029:self.eps29,2030:self.eps30}
    def validate(self):
        if not (1<self.spot<20000): raise ValueError('spot out of range')
        if not (100<=self.n_paths<=50000): raise ValueError('n_paths out of range')
        if self.initial_regime not in REGIMES: raise ValueError('unknown regime')
        if not (0<=self.initial_credit_stress<=2):raise ValueError('credit stress out of range')
        if not (0<=self.credit_long_run<=2):raise ValueError('long run credit out of range')
        if not (.25<=self.credit_persistence<=1):raise ValueError('credit persistence out of range')
        if not (0<=self.sentiment_persistence<1):raise ValueError('sentiment persistence out of range')
        if not (0<=self.switching_tendency<=3):raise ValueError('switching_tendency out of range')
        if not (0<=self.initial_lookthrough_weight<=.50):raise ValueError('look-through weight out of range')
        if any(v<=0 for v in self.earnings().values()):raise ValueError('nonpositive EPS')
        if not (0<=self.earnings_scenario_spread<=2):raise ValueError('earnings scenario spread out of range')

def load_events(path:Path|str|None=None) ->pd.DataFrame:
    e=(pd.DataFrame(json.loads((INPUTS/'demo.json').read_text(encoding='utf-8'))['events'])
       if path is None else pd.read_csv(path)).fillna('')
    required={'month','catalyst','upside_evidence','downside_evidence','timing',
              'prob_positive','revelation_chance','materiality','status'}
    if not required.issubset(e.columns):raise ValueError('missing event fields')
    if sorted(e.month.tolist())!=[str(m) for m in MONTHS]:
        raise ValueError('need exactly Nov 2026–Oct 2028, one row each')
    e=e.sort_values('month').reset_index(drop=True)
    for c in ['prob_positive','revelation_chance','materiality']:
        e[c]=pd.to_numeric(e[c],errors='raise')
    if not e.prob_positive.between(0,1).all() or not e.revelation_chance.between(0,1).all():
        raise ValueError('probabilities need range [0,1]')
    if not e.materiality.between(0,3).all():raise ValueError('materiality out of range')
    if not e.status.isin(['pending','positive','negative','neutral']).all():
        raise ValueError('status pending/positive/negative/neutral')
    return e

def load_history(path:Path|str=INPUTS/'amd_peer_history.csv')->dict[str,Any]:
    h=pd.read_csv(path)
    h=h[(h.iloc[:,0]>='2024-11')&(h.iloc[:,0]<='2026-09')]
    p=np.log1p(h.Peer_5_Return.to_numpy(dtype=float))
    a=np.log1p(h.AMD_Return.to_numpy(dtype=float))
    beta=float(np.cov(p,a,ddof=1)[0,1]/np.var(p,ddof=1))
    resid=a - (np.mean(a)-beta*np.mean(p)) - beta*p
    return {'peer':p-p.mean(),'idio':resid-resid.mean(),'beta':beta,'n':len(p),
            'peer_std':float(np.std(p,ddof=1)),
            'idio_std':float(np.std(resid,ddof=1)),
            'amd_std':float(np.std(a,ddof=1))}

def _ntm(month:pd.Period,eps:dict[int,float],ahead:int=0)->float:
    y=month.year+ahead
    w=month.month/12
    if y+1 not in eps:raise ValueError('missing year '+str(y+1))
    return (1-w)*eps[y]+w*eps[y+1]

def _eps_matrices(settings:Settings,scenario_eps=None):
    scenario_eps=SCENARIO_EPS if scenario_eps is None else scenario_eps
    # Base scenario is user-editable; slowdown/acceleration are adjusted to stay
    # the same proportional distance from the edited base as in the frozen snapshot.
    base=settings.earnings()
    out=[]
    for name in SCENARIO_LABELS:
        anchor=scenario_eps['reference']
        out.append({y:base[y]*(1+settings.earnings_scenario_spread*(scenario_eps[name][y]/anchor[y]-1)) for y in base})
    ntm=np.asarray([[_ntm(m,row) for row in out] for m in [START,*MONTHS]])
    ahead=np.asarray([[_ntm(m,row,ahead=1) for row in out] for m in [START,*MONTHS]])
    return ntm, ahead

def _softmax(scores):
    x=np.clip(scores-np.max(scores,axis=1,keepdims=True),-40,0)
    a=np.exp(x)
    return a/np.sum(a,axis=1,keepdims=True)

def _eps_mix(weights,ntm,ahead,w):
    a=np.sum(weights*ntm[None,:],axis=1)
    b=np.sum(weights*ahead[None,:],axis=1)
    return (1-w)*a+w*b

def _regime_lookthrough(state,postbull,settings,prior=PRIOR):
    # Higher conviction can cause the market to price farther forward, but
    # the effect is bounded and always relative to the starting scenario anchor.
    optimism=np.maximum(state-settings.initial_regime,0)
    v=settings.initial_lookthrough_weight+.068*optimism+.10*(postbull-prior[2])
    return np.clip(v,.03,.62)

def _baseline(settings,ntm,ahead,prior=PRIOR):
    # This remains a REFERENCE valuation construct, not a fair-value claim.
    base_earnings=(1-settings.initial_lookthrough_weight)*(ntm@prior)+settings.initial_lookthrough_weight*(ahead@prior)
    m0=settings.spot/base_earnings[0]
    t=np.arange(25,dtype=float)
    multiple=settings.stabilized_forward_pe+(m0-settings.stabilized_forward_pe)*np.exp(-t/settings.pe_normalization_months)
    return base_earnings*multiple,base_earnings,multiple

def run_model(settings:Settings,events:pd.DataFrame|None=None,*,prior=None,scenario_eps=None,regime_log_premiums=None):
    prior=PRIOR if prior is None else np.asarray(prior,dtype=float)
    regime_log_premiums=REGIME_LOG_PREMIUM if regime_log_premiums is None else np.asarray(regime_log_premiums,dtype=float)
    settings.validate()
    if events is None:events=load_events()
    if len(events)!=24:raise ValueError('24 events required')
    hist=load_history()
    rng=np.random.default_rng(settings.seed)
    n=settings.n_paths
    ntm,ahead=_eps_matrices(settings,scenario_eps)
    baseline,base_eps,baseline_pe=_baseline(settings,ntm,ahead,prior)
    assert abs(baseline[0]-settings.spot)<1e-9
    paths=np.zeros((n,25));paths[:,0]=settings.spot
    states=np.full((n,25),settings.initial_regime,dtype=np.int8)
    stress=np.zeros((n,25));stress[:,0]=settings.initial_credit_stress
    scenario_weights=np.broadcast_to(prior,(n,3)).copy()
    odds=np.zeros((n,25,3));odds[:,0,:]=prior
    d=np.zeros(n);momentum=np.zeros(n)
    sentiment_log_residual=np.zeros((n,25),dtype=float)
    duration=np.zeros(n,dtype=int)
    latent=rng.choice(3,size=n,p=prior)
    ids=np.arange(n)
    revealed_counts=np.zeros(n,int)
    for t,row in enumerate(events.itertuples(index=False),1):
        prob=float(row.prob_positive)
        relevance=float(row.materiality)*settings.evidence_strength
        spread=np.clip(settings.scenario_discrimination*min(relevance,1.6),0,.35)
        likelihood=np.clip(np.array([prob-spread,prob,prob+spread]),.035,.965)
        # An underlying scenario exists per path: observed evidence is more
        # likely to be positive if fundamentals truly support acceleration.
        if row.status=='pending':
            published=rng.random(n)<float(row.revelation_chance)
            outcome=rng.random(n)<likelihood[latent]
        elif row.status=='positive':
            published=np.ones(n,dtype=bool);outcome=np.ones(n,dtype=bool)
        elif row.status=='negative':
            published=np.ones(n,dtype=bool);outcome=np.zeros(n,dtype=bool)
        else:
            published=np.zeros(n,dtype=bool);outcome=np.zeros(n,dtype=bool)
        prev_bull=scenario_weights[:,2].copy()
        target=np.where(outcome[:,None],likelihood[None,:],1-likelihood[None,:])
        updated=scenario_weights*target
        updated/=updated.sum(axis=1,keepdims=True)
        scenario_weights=np.where(published[:,None],updated,scenario_weights)
        odds[:,t]=scenario_weights
        revealed_counts+=published.astype(int)
        # For a user-supplied observed outcome, condition subsequent unknown
        # future evidence on the updated posterior for the latent case.
        if row.status in ('positive','negative'):
            thresholds=np.cumsum(scenario_weights,axis=1)
            latent=np.sum(rng.random(n)[:,None]>thresholds,axis=1).clip(0,2)

        prev_credit=stress[:,t-1]
        credit_change_news=np.where(published,np.where(outcome,-.11,.12)*min(relevance,1.5),0.)
        new_credit=(settings.credit_persistence*prev_credit
              +(1-settings.credit_persistence)*settings.credit_long_run
              +rng.normal(0,settings.credit_monthly_noise,n)+credit_change_news)
        stress[:,t]=new_credit=np.clip(new_credit,0,2)

        peer=rng.choice(hist['peer'],size=n)*settings.peer_shock_scale
        idio=rng.choice(hist['idio'],size=n)*settings.idio_shock_scale
        old_state=states[:,t-1]
        # Future event windows are scenario assumptions; their outcomes and state-change dates
        # are not. Switching probabilities are SUBJECTIVE, not historically fitted.
        evidence_update=scenario_weights[:,2]-prev_bull
        signal=(2.2*evidence_update+1.9*(prev_credit-new_credit)
             +2.0*peer+.8*np.clip(momentum,-.35,.35)-.50*(new_credit-.70))
        hazard=(.075+.065*np.minimum(duration,12)/12
               +.12*np.abs(evidence_update)+.11*np.abs(new_credit-prev_credit))
        hazard=np.clip(hazard*settings.switching_tendency,0,.85)
        switching=rng.random(n)<hazard
        # Choose destination from genuinely different regimes. Rejected
        # out-of-bound steps no longer reset the state duration counter.
        diff=np.abs(REGIMES[None,:]-old_state[:,None])
        scores=(REGIMES[None,:]*signal[:,None]*1.5-.7*diff-.12*np.abs(REGIMES)[None,:])
        scores=np.where(REGIMES[None,:]==old_state[:,None],-1000,scores)
        candidates=np.cumsum(_softmax(scores),axis=1)
        r=rng.random(n)
        next_idx=np.sum(r[:,None]>candidates,axis=1).clip(0,4)
        new_state=np.where(switching,REGIMES[next_idx],old_state)
        states[:,t]=new_state
        duration=np.where(switching,0,duration+1)

        # Undirected/unexplained PRICE innovations affect only valuation,
        # not the Bayesian fundamental EPS posterior. No automatic negative
        # drift for months spent in pessimism, nor automatic positive drift
        # for months spent euphoric.
        amp=np.where(np.abs(new_state)==2,1.22,1)
        noise=amp*(hist['beta']*peer+idio)
        signfeedback=np.where(new_state<0,settings.pessimism_feedback,
                              np.where(new_state>0,settings.optimism_feedback,0.65))
        feedback=(settings.momentum_feedback*signfeedback*
                  np.tanh(momentum*3)*.06) # bounded monthly feedback
        d=settings.sentiment_persistence*d + noise + feedback
        # Saturation is soft (not a fixed minimum/maximum stock price).
        d=1.25*np.tanh(d/1.25)
        sentiment_log_residual[:,t]=d

        w=_regime_lookthrough(new_state,scenario_weights[:,2],settings,prior)
        eps_now=_eps_mix(scenario_weights,ntm[t],ahead[t],w)
        # reference denominator uses unchanged initial priors & lookthrough
        posterior_effect=np.log(eps_now/base_eps[t])
        regime_effect=regime_log_premiums[new_state+2]-regime_log_premiums[settings.initial_regime+2]
        credit_effect=-settings.credit_price_sensitivity*(new_credit-settings.initial_credit_stress)
        # The SAME starting panic state is already in the anchor. Therefore
        # credit and regime affect future price through CHANGES IN STATE ONLY.
        log_mkt=posterior_effect+regime_effect+credit_effect+d
        paths[:,t]=baseline[t]*np.exp(np.clip(log_mkt,-2.4,2.4))
        logret=np.log(paths[:,t]/paths[:,t-1])
        momentum=np.clip(.65*momentum+.35*logret,-.5,.5)

    p10,p25,p50,p75,p80,p90=np.quantile(paths,[.10,.25,.50,.75,.80,.90],axis=0)
    df=pd.DataFrame({'month':[str(START)]+[str(m) for m in MONTHS],
       'blue_earnings_reference':np.round(baseline,2),
       'orange_optimistic_p80':np.round(p80,2),
       'green_integrated_median':np.round(p50,2),
       'p10':np.round(p10,2),'p25':np.round(p25,2),
       'p75':np.round(p75,2),'p90':np.round(p90,2),
       'reference_expected_eps':np.round(base_eps,3),
       'reference_pe':np.round(baseline_pe,2),
       'prob_panic':np.round((states==-2).mean(axis=0),4),
       'prob_optimistic_or_euphoric':np.round((states>=1).mean(axis=0),4),
       'mean_prob_slowdown':np.round(odds[:,:,0].mean(axis=0),4),
       'mean_prob_acceleration':np.round(odds[:,:,2].mean(axis=0),4),
       'median_credit_stress':np.round(np.median(stress,axis=0),3)})
    levels=[500,600,700,800,900,1000,1200]
    touch={str(p):float(np.mean(np.max(paths[:,1:],axis=1)>=p)) for p in levels}
    meta={'as_of':'2026-10-18','spot_as_of':START_DATE,
          'simulation_paths':n,'seed':settings.seed,
          'calibration':{k:v for k,v in hist.items() if not isinstance(v,np.ndarray)},
          'method_note':'Green is monthwise median, orange is monthwise 80th percentile OF SAME distribution; not coherent individual trading paths.',
          'limitations':'Underspecified scenario priors, Bayesian likelihoods, regime transition hazards, future credit process and peer normalization. NOT empirically calibrated probabilities. 23 months is insufficient to estimate tails. User-supplied scenario anchor dated 2026-10-16; future dates require data refresh.'}
    return {'monthly':df,'paths':paths,'states':states,'credit':stress,'beliefs':odds,
            'touches':touch,'meta':meta,'settings':asdict(settings),'events':events,
            'sentiment_log_residual':sentiment_log_residual}

def chart_plotly(result,show_band=True,show_samples=False,individual_path=0,selector=None):
    import plotly.graph_objects as go
    df=result['monthly']
    fig=go.Figure()
    if show_band:
        fig.add_scatter(x=df.month,y=df.p90,mode='lines',line=dict(width=0),hoverinfo='skip',showlegend=False)
        fig.add_scatter(x=df.month,y=df.p10,mode='lines',line=dict(width=0),fill='tonexty',
          fillcolor='rgba(149,156,170,0.14)',name='Integrated P10–P90 scenario envelope',hoverinfo='skip')
    if show_samples:
        paths=result['paths'];n=len(paths)
        inds=np.linspace(0,n-1,10,dtype=int)
        for j,i in enumerate(inds):
            fig.add_scatter(x=df.month,y=paths[i],mode='lines',line=dict(width=1,color='rgba(165,165,165,0.24)'),
                    showlegend=j==0,name='Individual stochastic paths (illustrations)',hoverinfo='skip')
        if 0<=individual_path<n:
            fig.add_scatter(x=df.month,y=paths[individual_path],mode='lines',line=dict(color='#D084D6',width=1.8,dash='dot'),
                name=f'Simulated path #{individual_path} (not a forecast)')
    for col,name,color,w in [
      ('blue_earnings_reference','Blue: EPS × forward-multiple reference','#6BA9E7',3.2),
      ('orange_optimistic_p80','Amber: optimistic outcome (P80)','#D7A148',3),
      ('green_integrated_median','Green: integrated median (P50)','#31B3A3',3.5)]:
        fig.add_scatter(x=df.month,y=df[col],mode='lines+markers',
            name=name,line=dict(color=color,width=w),marker=dict(size=4),
            hovertemplate='%{x}: $%{y:,.0f}<extra>%{fullData.name}</extra>')
    if selector is not None:
        fig.add_scatter(x=selector.month,y=selector.smart_selected_price,mode='lines+markers',
           name='Magenta: adaptive P10–P90 selector (conditional scenario)',
           line=dict(color='#E07BD8',width=3.4),marker=dict(size=5),
           customdata=np.stack([selector.smart_percentile,selector.market_type],axis=1),
           hovertemplate='%{x}: $%{y:,.0f} • P%{customdata[0]} • %{customdata[1]}<extra>%{fullData.name}</extra>')
    fig.update_layout(title='AMD | Market-regime model + adaptive percentile selector (October 2026)',
        height=610,template='plotly_dark',xaxis_title=None,yaxis_title='USD/share',
        yaxis=dict(tickprefix='$',rangemode='tozero'),hovermode='x unified',
        legend=dict(orientation='h',x=0,y=-.20),margin=dict(l=60,r=20,t=68,b=110),
        paper_bgcolor='#10131D',plot_bgcolor='#10131D',font=dict(color='#E2E8F0'),
        xaxis=dict(tickangle=-45,nticks=13))
    return fig
