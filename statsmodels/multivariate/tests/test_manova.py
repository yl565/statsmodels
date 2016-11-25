# -*- coding: utf-8 -*-

import pandas as pd
from statsmodels.multivariate.manova import MANOVA
from numpy.testing import assert_almost_equal

# Example data
# https://support.sas.com/documentation/cdl/en/statug/63033/HTML/default/
#     viewer.htm#statug_introreg_sect012.htm
X = pd.DataFrame([['Minas Graes', 2.068, 2.070, 1.580],
                  ['Minas Graes', 2.068, 2.074, 1.602],
                  ['Minas Graes', 2.090, 2.090, 1.613],
                  ['Minas Graes', 2.097, 2.093, 1.613],
                  ['Minas Graes', 2.117, 2.125, 1.663],
                  ['Minas Graes', 2.140, 2.146, 1.681],
                  ['Matto Grosso', 2.045, 2.054, 1.580],
                  ['Matto Grosso', 2.076, 2.088, 1.602],
                  ['Matto Grosso', 2.090, 2.093, 1.643],
                  ['Matto Grosso', 2.111, 2.114, 1.643],
                  ['Santa Cruz', 2.093, 2.098, 1.653],
                  ['Santa Cruz', 2.100, 2.106, 1.623],
                  ['Santa Cruz', 2.104, 2.101, 1.653]],
                 columns=['Loc', 'Basal', 'Occ', 'Max'])


def test_manova_sas_example():
    mod = MANOVA.from_formula('Basal + Occ + Max ~ Loc', data=X)
    r = mod.hypothesis_testing
    assert_almost_equal(r[1][1].loc["Wilks’ lambda", 'Pr > F'],
                        0.6032, decimal=4)
    assert_almost_equal(r[1][1].loc["Pillai’s trace", 'Pr > F'],
                        0.5397, decimal=4)
    assert_almost_equal(r[1][1].loc["Hotelling-Lawley trace", 'Pr > F'],
                        0.6272, decimal=4)
    assert_almost_equal(r[1][1].loc["Roy’s greatest root", 'Pr > F'],
                        0.4109, decimal=4)
    mod = MANOVA.from_formula('Basal + Max ~ Loc*Occ', data=X)
