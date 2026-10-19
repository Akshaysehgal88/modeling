# Company inputs, units and sources

The focus list has 20 companies. It is curated around semiconductors, memory,
storage and AI infrastructure; it is not a market-cap ranking. All new presets
were prepared on 19 October 2026, with 16 October 2026 price/FX anchors and
completed monthly calibration observations ending September 2026.

## Annual EPS references

These are disclosed historical references, not the forward EPS curves. The
full period, units, accounting basis, source location and review date are stored
in each company JSON. Where a precise publication date was not verified, it is
left null instead of invented.

| Company | Historical EPS reference | Period and basis | Source |
| --- | --- | --- | --- |
| AMD | Original supplied forecast inputs | Original snapshot | Original user-supplied input |
| NVDA | USD 4.77 | FY2026 non-GAAP diluted | [Issuer source](https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Announces-Financial-Results-for-Fourth-Quarter-and-Fiscal-2026/) |
| AVGO | USD 6.82 | FY2025 non-GAAP diluted | [Issuer source](https://investors.broadcom.com/news-releases/news-release-details/broadcom-inc-announces-fourth-quarter-and-fiscal-year-2025) |
| INTC | USD 0.42 | FY2025 non-GAAP diluted | [Issuer source](https://www.intc.com/news-events/press-releases/detail/1759/intel-reports-fourth-quarter-and-full-year-2025-financial) |
| QCOM | USD 12.03 | FY2025 non-GAAP diluted | [Issuer source](https://www.qualcomm.com/news/releases/2025/11/qualcomm-announces-fourth-quarter-and-fiscal-2025-results) |
| MU | USD 75.52 | FY2026 non-GAAP diluted | [Issuer source](https://investors.micron.com/news/press-release/2026/Micron-Technology-Inc--Reports-Record-Fiscal-Fourth-Quarter-and-Full-Year-2026-Results/) |
| SNDK | USD 70.88 | FY2026 non-GAAP diluted | [Issuer source](https://investor.sandisk.com/news-releases/news-release-details/sandisk-reports-fiscal-fourth-quarter-2026-financial-results) |
| WDC | USD 10.22 | FY2026 non-GAAP diluted | [Issuer source](https://investor.wdc.com/news-releases/news-release-details/wd-reports-fiscal-fourth-quarter-and-fiscal-year-2026-financial) |
| STX | USD 15.58 | FY2026 non-GAAP diluted | [Issuer source](https://investors.seagate.com/news/news-details/2026/Seagate-Technology-Reports-Fiscal-Fourth-Quarter-and-Fiscal-Year-2026-Financial-Results/) |
| MRVL | USD 2.84 | FY2026 non-GAAP diluted | [Issuer source](https://investor.marvell.com/news-events/press-releases/detail/1011/marvell-technology-inc-reports-fourth-quarter-and-fiscal-year-2026-financial-results) |
| TSMC | TWD 66.26 | FY2025 Taiwan IFRS diluted | [Issuer source](https://investor.tsmc.com/static/annualReports/2025/english/index.html) |
| SAMSUNG | KRW 6603 | FY2025 K-IFRS consolidated diluted ordinary | [Issuer source](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2025_con_quarter04_all.pdf) |
| SKHYNIX | KRW 60378 | FY2025 K-IFRS consolidated diluted | [Issuer source](https://mis-prod-koce-homepage-cdn-01-blob-ep.azureedge.net/web/attach/121822586381465204.pdf) |
| ASML | EUR 24.73 | FY2025 US GAAP basic | [Issuer source](https://investor.asml.com/news-releases/news-release-details/q4-2025-financial-results) |
| AMAT | USD 9.42 | FY2025 non-GAAP diluted | [Issuer source](https://ir.appliedmaterials.com/news-releases/news-release-details/applied-materials-announces-fourth-quarter-and-fiscal-year-2025) |
| LRCX | USD 5.82 | FY2026 non-GAAP diluted | [Issuer source](https://investor.lamresearch.com/image/Q4_2026_slides_final.pdf) |
| KLAC | USD 3.66 | FY2026 US GAAP diluted; June 2026 10-for-1 split adjusted | [Issuer source](https://ir.kla.com/news-events/press-releases/detail/518/kla-corporation-reports-fiscal-2026-fourth-quarter-and-full) |
| ARM | USD 1.77 | FY2026 non-GAAP diluted per ordinary share / ADS | [Issuer source](https://investors.arm.com/static-files/344cbcfe-e28b-48ab-b272-c856e0756a91) |
| ADI | USD 7.79 | FY2025 non-GAAP adjusted diluted | [Issuer source](https://investor.analog.com/news-releases/news-release-details/analog-devices-reports-strong-fourth-quarter-and-fiscal-2025) |
| NXPI | USD 11.81 | FY2025 non-GAAP diluted | [Issuer source](https://investors.nxp.com/news-releases/news-release-details/nxp-semiconductors-reports-fourth-quarter-and-full-year-2025) |

The original AMD assumptions remain intact. Its separate historical issuer
register remains background information rather than replacing its forecasts.

## Specific unit and accounting checks

- Samsung: Note 26(A)(2) of the consolidated financial statements, PDF page 75,
  gives KRW 6,603 diluted EPS per ordinary share. The standalone and preference
  share tables are different; they are not substituted.
- SK hynix: consolidated Note 30(2), PDF page 87, gives KRW 60,378 diluted EPS.
  The preset uses the Korean ordinary share, not a USD depositary receipt.
- TSMC: use NT$66.26 from the later annual website summary. The January management
  report gives NT$66.25; this minor difference is recorded in source notes.
  The listing is 2330.TW, and EPS and quote are both per ordinary share in TWD.
- ASML: the FY2025 release labels EUR 24.73 as basic EPS. The preset preserves
  that basis and uses the Amsterdam EUR listing.
- KLA: its July 2026 release explicitly restates per-share values for the June
  2026 ten-for-one stock split. The GAAP diluted annual EPS reference is $3.66.
- Arm: the reference is non-GAAP EPS per ordinary share. Each Nasdaq ADS
  represents one ordinary share, as stated in its
  [2026 depositary notice filing](https://www.sec.gov/Archives/edgar/data/1973239/000197323926000117/arm-20260810.htm).
- Intel: the positive annual reference is non-GAAP EPS, not a relabeled GAAP loss.

## Market data and calibration

New price anchors and adjusted monthly prices come from the publicly accessible
Yahoo Finance chart endpoint. Each profile includes exact dated request URLs,
retrieval dates, currency, peer identifiers and adjustment method. These market
observations are provider data, separate from issuer financial disclosures.

The builder groups bars using the exchange's local timezone, excludes partial
October 2026 bars, computes simple returns from split/dividend-adjusted monthly
prices and averages five explicit native-return peers equally. It retains only
complete asset/peer pairs. No forward filling, zero filling, borrowed AMD returns
or synthetic series is used. Calibration applies the original covariance-beta,
residual and bootstrap mechanism to those pairs.

The supplied AMD calibration is kept unchanged. New presets normally have 23
pairs; SanDisk has 19, reflecting the feed's shorter standalone history. WDC's
2025 SanDisk separation changes business comparability across its historical
window. Short history, corporate restructuring and adjusted-return conventions
limit the strength of any inference. They do not establish calibrated tails.

Calibration datasets are distinct files. Validation rejects a dataset or peer
basket from the wrong company. Each dataset's bytes are hashed in audit output.

## Forecast assumptions

Company-specific annual growth vectors, three EPS curves, valuation multiple,
initial credit/regime assumptions and business-driver checkpoints are inspectable
in the preset and `definitions.json`. They are authored demo scenarios, not
consensus estimates or guaranteed guidance. Common mathematical coefficients
remain the original mechanism. Market sensitivities, EPS, price, histories and
checkpoints are not filled with AMD's company-specific inputs.

Fiscal labels retain issuer conventions, while monthly interpolation retains the
original calendar-month approximation. The same 24-month model grid is used for
all companies. Negative-EPS valuation is outside this positive-EPS/P-E engine's
scope; the basis of any positive historical reference is recorded explicitly.

## Currency and reproducibility

Native USD/EUR/KRW/TWD inputs are never converted before simulation. Won-denominated
values can exceed the old USD-specific input bounds. No scaling changes the
mathematical price process. Optional display FX scales prices and EPS together;
P/E, returns, probabilities and selector ranks stay unchanged. Price-level touch
statistics remain explicitly labeled in native currency in the audit.

FX is a dated public snapshot. It can be manually overridden, in which case the
export identifies it as a user assumption. Scenario JSON always stores native
assumptions; audit JSON additionally stores presentation currency and rate.

Profiles are packaged offline. Rebuilding from cached observations preserves the
snapshot; refreshing uses explicit request dates but provider histories may be
revised. Keep the source hashes and package/runtime versions with a published run.
