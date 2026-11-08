# Data notice

## Dataset

This project uses the **Online Retail** dataset published by the UCI Machine
Learning Repository.

- Creator: Daqing Chen (London South Bank University)
- Source: <https://archive.ics.uci.edu/dataset/352/online+retail>
- DOI: <https://doi.org/10.24432/C5BW33>
- Coverage: 2010-12-01 to 2011-12-09
- Rows: 541,909 transactions before de-duplication
- License: **Creative Commons Attribution 4.0 International (CC BY 4.0)**

The dataset describes transactions of a UK-based, registered non-store online
retailer. The company mainly sells unique all-occasion gifts, and many of its
customers are wholesalers.

## What is committed to this repository

`data/raw/online_retail.csv.gz` is a compressed, column-renamed copy of the
public dataset. It is included so that every chart in this repository can be
reproduced offline. The original column names are documented in
[`docs/methodology.md`](../docs/methodology.md).

`data/sample/online_retail_sample.csv` is a 12,000-row head sample used by the
test suite and CI.

## Attribution

If you reuse the data, keep the attribution above and cite:

> Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning Repository.
> https://doi.org/10.24432/C5BW33

The **code** in this repository is licensed under the MIT License (see
[`LICENSE`](../LICENSE)). The **dataset** remains under CC BY 4.0; the MIT
License does not replace the dataset license.

## Privacy

Customer IDs are anonymised five-digit identifiers provided by UCI. No names,
addresses, emails, or payment data are present. The analysis reports aggregates
and does not attempt to re-identify anyone.
