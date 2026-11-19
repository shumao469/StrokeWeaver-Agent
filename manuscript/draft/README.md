# StrokeWeaver manuscript draft

This directory contains the research manuscript draft, supplementary information and editable figure deck associated with StrokeWeaver. These are draft materials for scientific discussion and author review. The executable 1.0 and 2.0 software demonstrations continue to operate on generated inputs and recorded generated-input traces, as described in their separate documentation.

| File | Content |
| --- | --- |
| [StrokeWeaver_Article.docx](StrokeWeaver_Article.docx) | Editable manuscript with figure legends |
| [StrokeWeaver_Supplementary.docx](StrokeWeaver_Supplementary.docx) | Editable supplementary methods and tables |
| [StrokeWeaver_Figures_editable.pptx](StrokeWeaver_Figures_editable.pptx) | Editable portrait figures, including extended data and supplementary figures |

## Image sources and reuse

- **SOOP image example.** Figure 1 includes de-identified axial TRACE and ADC images from the public [SOOP OpenNeuro dataset ds004889 v1.1.2](https://doi.org/10.18112/openneuro.ds004889.v1.1.2), and an overlay of a local model score. The dataset's [official description](https://raw.githubusercontent.com/OpenNeuroDatasets/ds004889/master/dataset_description.json) identifies the dataset license as CC0. This image example is separate from the generated-input replay illustrated alongside it. Dataset descriptor: Absher et al., [Scientific Data 11, 839 (2024)](https://doi.org/10.1038/s41597-024-03667-5).
- **Published DeepISLES examples.** Figure 2d includes two cropped examples from Fig. 5 of de la Rosa et al., [DeepISLES: a clinically validated ischemic stroke segmentation model from the ISLES’22 challenge](https://doi.org/10.1038/s41467-025-62373-x), *Nature Communications* 16, 7357 (2025). The original article is licensed under [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/). The original images have been cropped and placed in a new multi-panel figure. The examples and Fig. 1e benchmark belong to the published DeepISLES evaluation and its Johns Hopkins cohort.
- **Generated examples.** Figures and traces marked generated or synthetic represent controlled computational inputs, fault injections or exact finite models. Each reported comparison retains its stated unit of analysis and timing scope.

The original DeepISLES article's license states that third-party material is included unless otherwise indicated in its credit line. Users should preserve the applicable attribution and check any separate credit line when reusing material.

## Availability and review

The manuscript includes a worked SOOP image example, generated engineering tests and an APIS source-development diagnostic. Model weights, patient-level data, protected labels and credentials are not included. See the [reproducibility guide](../../StrokeWeaver-2.0/REPRODUCIBILITY.md) for the public replay version, commands, figure-specific availability, external resources and timing boundaries.

The correspondence, author contributions, funding, competing interests, ethics and data-use statements are to be reviewed and completed by the authors for the intended submission. The draft and figure deck may change following that review. Local filesystem paths have been removed from the public figure deck's speaker notes; figure text, objects, images and source citations remain available for review.

