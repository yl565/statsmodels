# -*- coding: utf-8 -*-

"""Multivariate analysis of variance

author: Yichuan Liu
"""
from __future__ import print_function, division

from statsmodels.base.model import Model
import numpy as np
from numpy.linalg import eigvals, inv, pinv, matrix_rank, qr, svd, solve
from scipy import stats
import pandas as pd
from statsmodels.iolib import summary2


def fit_manova(x, y):
    """
    MANOVA fitting y = x * params
    where y is dependent variables, x is independent variables

    Parameters
    ----------
    x : array-like, each column is a independent variable
    y : array-like, each column is a dependent variable

    Returns
    -------
    a tuple of matrices or values necessary for hypothesis testing

    """
    nobs, k_endog = y.shape
    nobs1, k_exog= x.shape
    if nobs != nobs1:
        raise ValueError('x(n=%d) and y(n=%d) should have the same number of '
                         'rows!' % (nobs1, nobs))

    # Calculate the matrices necessary for hypothesis testing
    df_resid = nobs - k_exog

    # Regression coefficients matrix
    params = pinv(x).dot(y)

    # inverse of x'x
    inv_cov = inv(x.T.dot(x))

    # Sums of squares and cross-products of residuals
    # Y'Y - (X * params)'B * params
    t = x.dot(params)
    sscpr = np.subtract(y.T.dot(y), t.T.dot(t))
    return (params, df_resid, inv_cov, sscpr)


def multivariate_stats(eigenvals, p, q, df_resid):
    """
    Testing MANOVA statistics, see:
    https://support.sas.com/documentation/cdl/en/statug/63033/HTML/default/
    viewer.htm#statug_introreg_sect012.htm

    Parameters
    ----------
    eigenvals : array
        The eigenvalues of (E + H)^H matrix where `^` denote inverse
    p : int
        Rank of E + H
    q : int
        Rank of X
    df_resid
        Residual degree of freedom (n_samples minus n_variables of X)

    Returns
    -------

    """
    eigv2 = eigenvals
    eigv1 = np.array([i / (1 - i) for i in eigv2])
    v = df_resid

    s = np.min([p, q])
    m = (np.abs(p - q) - 1) / 2
    n = (v - p - 1) / 2

    results = pd.DataFrame({'Value': [], 'F Value': [], 'Num DF': [],
                            'Den DF': [], 'Pr > F': []})

    def fn(x):
        return np.real([x])[0]

    results.loc["Wilks’ lambda", 'Value'] = fn(np.prod(1 - eigv2))

    results.loc["Pillai’s trace", 'Value'] = fn(eigv2.sum())

    results.loc["Hotelling-Lawley trace", 'Value'] = fn(eigv1.sum())

    results.loc["Roy’s greatest root", 'Value'] = fn(eigv1.max())

    r = v - (p - q + 1)/2
    u = (p*q - 2) / 4
    df1 = p * q
    if p*p + q*q - 5 > 0:
        t = np.sqrt((p*p*q*q - 4) / (p*p + q*q - 5))
    else:
        t = 1
    df2 = r*t - 2*u
    lmd = results.loc["Wilks’ lambda", 'Value']
    lmd = np.power(lmd, 1 / t)
    F = (1 - lmd) / lmd * df2 / df1
    results.loc["Wilks’ lambda", 'Num DF'] = df1
    results.loc["Wilks’ lambda", 'Den DF'] = df2
    results.loc["Wilks’ lambda", 'F Value'] = F
    pval = stats.f.sf(F, df1, df2)
    results.loc["Wilks’ lambda", 'Pr > F'] = pval

    V = results.loc["Pillai’s trace", 'Value']
    df1 = s * (2*m + s + 1)
    df2 = s * (2*n + s + 1)
    F = df2 / df1 * V / (s - V)
    results.loc["Pillai’s trace", 'Num DF'] = df1
    results.loc["Pillai’s trace", 'Den DF'] = df2
    results.loc["Pillai’s trace", 'F Value'] = F
    pval = stats.f.sf(F, df1, df2)
    results.loc["Pillai’s trace", 'Pr > F'] = pval

    U = results.loc["Hotelling-Lawley trace", 'Value']
    if n > 0:
        b = (p + 2*n) * (q + 2*n) / 2 / (2*n + 1) / (n - 1)
        df1 = p * q
        df2 = 4 + (p*q + 2) / (b - 1)
        c = (df2 - 2) / 2 / n
        F = df2 / df1 * U / c
    else:
        df1 = s * (2*m + s + 1)
        df2 = s * (s*n + 1)
        F = df2 / df1 / s * U
    results.loc["Hotelling-Lawley trace", 'Num DF'] = df1
    results.loc["Hotelling-Lawley trace", 'Den DF'] = df2
    results.loc["Hotelling-Lawley trace", 'F Value'] = F
    pval = stats.f.sf(F, df1, df2)
    results.loc["Hotelling-Lawley trace", 'Pr > F'] = pval

    sigma = results.loc["Roy’s greatest root", 'Value']
    r = np.max([p, q])
    df1 = r
    df2 = v - r + q
    F = df2 / df1 * sigma
    results.loc["Roy’s greatest root", 'Num DF'] = df1
    results.loc["Roy’s greatest root", 'Den DF'] = df2
    results.loc["Roy’s greatest root", 'F Value'] = F
    pval = stats.f.sf(F, df1, df2)
    results.loc["Roy’s greatest root", 'Pr > F'] = pval
    return results.iloc[:, [4, 2, 0, 1, 3]]


def test_manova(results, contrast_L, transform_M=None):
    """
    MANOVA hypothesis testing

    For y = x * params, where y is dependent variables, x is independent
    variables testing L * params * M = 0 where L is the contast matrix for
    hypothesis testing and M is the transformation matrix for transforming the
    dependent variables in y.

    Testing is based on forming the following matrices:
        H = M'(L * params)'(L * inv_cov * L')^(L * params)M   (`^` denotes inverse)
        E = M' * sscpr * M
    And then solving the eigenvalues of (E + H)^ * H

    .. [1] https://support.sas.com/documentation/cdl/en/statug/63033/HTML/
default/viewer.htm#statug_introreg_sect012.htm

    Parameters
    ----------
    fit_output : tuple
        Output of ``fit_manova``
    contrast_L : array-like
        Contrast matrix for hypothesis testing. Each row is an hypothesis and
        each column is an independent variable.
        At least 1 row (1 by k_exog, the number of independent variables)
    transform_M : array-like
        Transform matrix. Default to be k_endog by k_endog identity
        matrix (i.e. do not transform y matrix).

    Returns
    -------
    results : MANOVAResults

    """
    params, df_resid, inv_cov, sscpr = results
    M = transform_M
    if M is None:
        M = np.eye(params.shape[1])
    L = contrast_L
    # t1 = (L * params)M
    t1 = L.dot(params).dot(M)

    # H = t1'L(X'X)^L't1
    t2 = L.dot(inv_cov).dot(L.T)
    q = matrix_rank(t2)
    H = t1.T.dot(inv(t2)).dot(t1)

    # E = M'(Y'Y - B'(X'X)B)M
    E = M.T.dot(sscpr).dot(M)

    EH = np.add(E, H)
    p = matrix_rank(EH)

    # eigenvalues of (E + H)^H
    eigv2 = np.sort(eigvals(inv(EH).dot(H)))
    return multivariate_stats(eigv2, p, q, df_resid)


class MANOVA(Model):
    """
    Multivariate analysis of variance


    Parameters
    ----------
    endog : array-like
        Dependent variables (DV). A n_sample x n_y_var array where n_sample is
        the number of observations and n_y_var is the number of DV.

    exog : array-like
        Independent variables (IV). A n_sample x n_x_var array where n is the
        number of observations and n_x_var is the number of IV. An intercept is
        not included by default and should be added by the user (models
        specified using a formula include an intercept by default)

    Attributes
    -----------
    df_resid : float
        The number of observation `n` minus the number of IV `q`.
    sscpr : array
        Sums of squares and cross-products of residuals
    endog : array
        See Parameters.
    exog : array
        See Parameters.
    design_info : patsy.DesignInfo
        Contain design info for the independent variables if model is
        constructed using `from_formula`

    """
    def __init__(self, endog, exog, design_info=None, **kwargs):
        self.design_info = design_info
        out = fit_manova(exog, endog)
        self.reg_coeffs, self.df_resid, self.inv_cov_, self.sscpr = out
        super(MANOVA, self).__init__(endog, exog)

    @classmethod
    def from_formula(cls, formula, data, subset=None, drop_cols=None,
                     *args, **kwargs):
        mod = super(MANOVA, cls).from_formula(formula, data,
                                              subset=subset,
                                              drop_cols=drop_cols,
                                              *args, **kwargs)
        return mod

    def test(self, hypothesis=None):
        """
        Testing the genernal hypothesis
            L * params * M = 0
        for each tuple (name, L, M) in `H` where `params` is the regression
        coefficient matrix for the linear model y = x * params

        Parameters
        ----------
        hypothesis: A list of tuples
           Hypothesis to be tested. Each element is a tuple (name, L, M)
           containing a string `name`, the contrast matrix L and the transform
           matrix M for transforming dependent variables, respectively. If M is
           `None`, it is set to an identity matrix (i.e. no dependent
           variable transformation).
           If `hypothesis` is None: 1) the effect of each independent variable
           on the dependent variables will be tested. Or 2) if model is created
           using a formula,  `hypothesis` will be created according to
           `design_info`. 1) and 2) is equivalent if no additional variables
           are created by the formula (e.g. dummy variables for categorical
           variables and interaction terms)

        Returns
        -------
        results: MANOVAResults

        """
        if hypothesis is None:
            if self.design_info is not None:
                terms = self.design_info.term_name_slices
                hypothesis = []
                for key in terms:
                    L_contrast = np.eye(self.exog.shape[1])[terms[key], :]
                    hypothesis.append((key, L_contrast, None))
            else:
                hypothesis = []
                for i in range(self.exog.shape[1]):
                    name = 'x%d' % (i)
                    L = np.zeros([1, self.exog.shape[1]])
                    L[i] = 1
                    hypothesis.append([name, L, None])

        results = []
        for name, L, M in hypothesis:
            if len(L.shape) != 2:
                raise ValueError('Contrast matrix L must be a 2-d array!')
            if L.shape[1] != self.exog.shape[1]:
                raise ValueError('Contrast matrix L should have the same '
                                 'number of columns as exog! %d != %d' %
                                 (L.shape[1], self.exog.shape[1]))
            if M is not None:
                if len(M.shape) != 2:
                    raise ValueError('Transform matrix M must be a 2-d array!')
                if M.shape[0] != self.endog.shape[1]:
                    raise ValueError('Transform matrix M should have the same '
                                     'number of rows as the number of columns '
                                     'of endog! %d != %d' %
                                     (M.shape[0], self.exog.shape[1]))
            fit_output = (self.reg_coeffs, self.df_resid, self.inv_cov_,
                          self.sscpr)
            manova_table = test_manova(fit_output, L, M)
            results.append((name, manova_table))
        return MANOVAResults(results)


class MANOVAResults(object):
    """
    MANOVA results class

    Can be accessed as a list, each element containing a tuple (name, df) where
    `name` is the effect (i.e. term in model) name and `df` is a DataFrame
    containing the MANOVA test statistics

    """
    def __init__(self, results):
        self.results = results

    def __str__(self):
        return self.summary().__str__()

    def __getitem__(self, item):
        return self.results[item]

    def summary(self):
        summ = summary2.Summary()
        summ.add_title('MANOVA results')
        for h in self.results:
            summ.add_dict({'Effect':h[0]})
            summ.add_df(h[1])
        return summ


class Cancorr(Model):
    """
    Canonical correlation analysis using singluar value decomposition

    For matrices x and y, find projections x_cancoef and y_cancoef such that:
        x1 = x * x_cancoef, x1' * x1 is identity matrix
        y1 = y * y_cancoef, y1' * y1 is identity matrix
    and the correlation between x1 and y1 is maximized.

    .. [1] http://numerical.recipes/whp/notes/CanonCorrBySVD.pdf
    .. [2] http://www.csun.edu/~ata20315/psy524/docs/Psy524%20Lecture%208%20CC.pdf
    .. [3] http://www.mathematica-journal.com/2014/06/canonical-correlation-analysis/
    """
    def __init__(self, endog, exog, design_info=None, **kwargs):
        self.design_info = design_info
        super(Cancorr, self).__init__(endog, exog)

    def fit(self):
        nobs, p = self.endog.shape
        nobs, q = self.exog.shape
        k = np.min([p, q])

        x = np.array(self.exog)
        x = x - x.mean(0)
        y = np.array(self.endog)
        y = y - y.mean(0)

        e = 1e-8  # eigenvalue tolerance, values smaller than e is considered 0
        ux, sx, vx = svd(x, 0)
        # vx_ds = vx.T divided by sx
        vx_ds = vx.T
        for i in range(len(sx)):
            if sx[i] > e:
                vx_ds[:, i] = vx_ds[:, i] / sx[i]
            else:
                break
        uy, sy, vy = svd(y, 0)
        # vy_ds = vy.T divided by sy
        vy_ds = vy.T
        for i in range(len(sy)):
            if sy[i] > e:
                vy_ds[:, i] = vy_ds[:, i] / sy[i]
            else:
                break
        u, s, v = svd(ux.T.dot(uy), 0)

        # Correct any roundoff
        self.cancorr = np.array([max(0, min(s[i], 1)) for i in range(len(s))])

        self.x_cancoef = vx_ds.dot(u[:, :k])
        self.y_cancoef = vy_ds.dot(v.T[:, :k])

        self.stats = pd.DataFrame()
        a = -(nobs - 1  - (p + q + 1)/2)
        eigenvals = np.power(self.cancorr, 2)
        prod = 1
        for i in range(len(eigenvals)-1, -1, -1):
            prod *= 1 - eigenvals[i]
            p1 = p - i
            q1 = q - i
            r = (nobs - q - 1) - (p1 - q1 + 1)/2
            u = (p1*q1 - 2) / 4
            df1 = p1 * q1
            if p1*p1 + q1*q1 - 5 > 0:
                t = np.sqrt((p1*p1*q1*q1 - 4) / (p1*p1 + q1*q1 - 5))
            else:
                t = 1
            df2 = r*t - 2*u
            lmd = np.power(prod,  1 / t)
            F = (1 - lmd) / lmd * df2 / df1
            self.stats.loc[i, "Wilks' lambda"] = prod
            self.stats.loc[i, 'Num DF'] = df1
            self.stats.loc[i, 'Den DF'] = df2
            self.stats.loc[i, 'F Value'] = F
            pval = stats.f.sf(F, df1, df2)
            self.stats.loc[i, 'Pr > F'] = pval
            '''
            # Wilk's Chi square test of each canonical correlation
            df = (p - i + 1) * (q - i + 1)
            chi2 = a * np.log(prod)
            pval = stats.chi2.sf(chi2, df)
            self.stats.loc[i, 'Canonical correlation'] = self.cancorr[i]
            self.stats.loc[i, 'Chi-square'] = chi2
            self.stats.loc[i, 'DF'] = df
            self.stats.loc[i, 'Pr > ChiSq'] = pval
            '''
        ind = self.stats.index.values[::-1]
        self.stats = self.stats.loc[ind, :]

        # Multivariate tests
        self.multi_stats = multivariate_stats(eigenvals,
                                              p, q, nobs - q - 1)

        return CancorrResults(self)

class CancorrResults(object):
    """
    Canonical correlation results class

    """
    def __init__(self, cancorr_obj):
        self.cancorr = cancorr_obj.cancorr
        self.x_cancoef = cancorr_obj.x_cancoef
        self.y_cancoef = cancorr_obj.y_cancoef
        self.multi_stats = cancorr_obj.multi_stats
        self.stats = cancorr_obj.stats

    def __str__(self):
        return self.summary().__str__()

    def summary(self):
        summ = summary2.Summary()
        summ.add_title('Cancorr results')
        summ.add_df(self.stats)
        summ.add_dict({'': ''})
        summ.add_dict({'Multivariate Statistics and F Approximations': ''})
        summ.add_df(self.multi_stats)
        return summ

