import torch
import numpy as np
import pytest

from torchdr.utils import (
    check_equality_torch_keops,
    check_similarity,
    check_symmetry,
    check_marginal,
    check_entropy,
    check_type,
    entropy,
)
from torchdr.utils import pairwise_distances
from torchdr.affinity import (
    ScalarProductAffinity,
    GibbsAffinity,
    StudentAffinity,
    log_Pe,
    bounds_entropic_affinity,
    EntropicAffinity,
    L2SymmetricEntropicAffinity,
    SymmetricEntropicAffinity,
    DoublyStochasticEntropic,
)

lst_types = [torch.double, torch.float]

LIST_METRICS_TEST = ["euclidean", "manhattan"]


@pytest.mark.parametrize("dtype", lst_types)
def test_scalar_product_affinity(dtype):
    n, p = 100, 10
    X = torch.randn(n, p, dtype=dtype)

    list_P = []
    for keops in [False, True]:
        affinity = ScalarProductAffinity(keops=keops)
        P = affinity.get(X)
        list_P.append(P)

        # -- check properties of the affinity matrix --
        check_type(P, keops=keops)
        assert P.shape == (n, n), "Affinity matrix shape is incorrect"
        check_symmetry(P)

    # --- check equality between torch and keops ---
    check_equality_torch_keops(list_P[0], list_P[1], K=10)


@pytest.mark.parametrize("dtype", lst_types)
def test_gibbs_affinity(dtype):
    n, p = 100, 10
    X = torch.randn(n, p, dtype=dtype)

    for metric in LIST_METRICS_TEST:
        list_P = []
        for keops in [False, True]:
            affinity = GibbsAffinity(keops=keops, metric=metric)
            P = affinity.get(X)
            list_P.append(P)

            # -- check properties of the affinity matrix --
            check_type(P, keops=keops)
            assert P.shape == (n, n), "Affinity matrix shape is incorrect"
            assert P.min() >= 0, "Affinity matrix has negative values"

        # --- check equality between torch and keops ---
        check_equality_torch_keops(list_P[0], list_P[1], K=10)


@pytest.mark.parametrize("dtype", lst_types)
def test_student_affinity(dtype):
    n, p = 100, 10
    X = torch.randn(n, p, dtype=dtype)

    for metric in LIST_METRICS_TEST:
        list_P = []
        for keops in [False, True]:
            affinity = StudentAffinity(keops=keops, metric=metric)
            P = affinity.get(X)
            list_P.append(P)

            # -- check properties of the affinity matrix --
            check_type(P, keops=keops)
            assert P.shape == (n, n), "Affinity matrix shape is incorrect"
            assert P.min() >= 0, "Affinity matrix has negative values"

        # --- check equality between torch and keops ---
        check_equality_torch_keops(list_P[0], list_P[1], K=10)


@pytest.mark.parametrize("dtype", lst_types)
def test_entropic_affinity(dtype):
    n, p = 100, 10
    perp = 5
    target_entropy = np.log(perp) + 1
    tol = 1e-5
    one = torch.ones(n, dtype=dtype)
    target_entropy = np.log(perp) * one + 1

    def entropy_gap(eps, C):  # function to find the root of
        return entropy(log_Pe(C, eps), log=True) - target_entropy

    X = torch.randn(n, p, dtype=dtype)

    for metric in LIST_METRICS_TEST:

        list_P = []
        for keops in [False, True]:
            affinity = EntropicAffinity(
                perplexity=perp, keops=keops, metric=metric, tol=tol, verbose=True
            )
            P = affinity.get(X)
            list_P.append(P)

            # -- check properties of the affinity matrix --
            check_type(P, keops=keops)
            assert P.shape == (n, n), "Affinity matrix shape is incorrect"
            check_marginal(P, one, dim=1)
            check_entropy(P, target_entropy, dim=1, tol=tol)

            # -- check bounds on the root of entropic affinities --
            C = pairwise_distances(X, metric=metric, keops=keops)
            begin, end = bounds_entropic_affinity(C, perplexity=perp)
            assert (
                entropy_gap(begin, C) < 0
            ).all(), "Lower bound of entropic affinity root is not valid"
            assert (
                entropy_gap(end, C) > 0
            ).all(), "Lower bound of entropic affinity root is not valid"

        # --- check equality between torch and keops ---
        check_equality_torch_keops(list_P[0], list_P[1], K=perp)


@pytest.mark.parametrize("dtype", lst_types)
def test_l2sym_entropic_affinity(dtype):
    n, p = 100, 10
    perp = 5

    X = torch.randn(n, p, dtype=dtype)

    for metric in LIST_METRICS_TEST:
        list_P = []
        for keops in [False, True]:
            affinity = L2SymmetricEntropicAffinity(
                perplexity=perp, keops=keops, metric=metric, verbose=True
            )
            P = affinity.get(X)
            list_P.append(P)

            # -- check properties of the affinity matrix --
            check_type(P, keops=keops)
            assert P.shape == (n, n), "Affinity matrix shape is incorrect"
            check_symmetry(P)

        # --- check equality between torch and keops ---
        check_equality_torch_keops(list_P[0], list_P[1], K=perp)


@pytest.mark.parametrize("dtype", lst_types)
def test_sym_entropic_affinity(dtype):
    n, p = 100, 10
    perp = 5
    tol = 1e-3
    one = torch.ones(n, dtype=dtype)
    target_entropy = np.log(perp) * one + 1

    X = torch.randn(n, p, dtype=dtype)

    for metric in LIST_METRICS_TEST:
        list_P = []
        for keops in [False, True]:
            affinity = SymmetricEntropicAffinity(
                perplexity=perp,
                keops=keops,
                metric=metric,
                tol=tol,
                tolog=True,
                verbose=True,
            )
            P = affinity.get(X)
            list_P.append(P)

            # -- check properties of the affinity matrix --
            check_type(P, keops=keops)
            assert P.shape == (n, n), "Affinity matrix shape is incorrect"
            check_symmetry(P)
            check_marginal(P, one, dim=1, tol=tol)
            check_entropy(P, target_entropy, dim=1, tol=tol)

            # --- test eps_square ---
            affinity_eps_square = SymmetricEntropicAffinity(
                perplexity=perp,
                keops=keops,
                metric=metric,
                tol=1e-5,
                eps_square=True,
                lr=1e-1,
            )
            P_eps_square = affinity_eps_square.get(X)
            check_similarity(P, P_eps_square, tol=tol)

        # --- check equality between torch and keops ---
        check_equality_torch_keops(list_P[0], list_P[1], K=perp)


@pytest.mark.parametrize("dtype", lst_types)
def test_doubly_stochastic_entropic(dtype):
    n, p = 100, 10
    eps = 1.0
    tol = 1e-3
    one = torch.ones(n, dtype=dtype)

    X = torch.randn(n, p, dtype=dtype)

    for metric in LIST_METRICS_TEST:
        list_P = []
        for keops in [False, True]:
            affinity = DoublyStochasticEntropic(eps=eps, keops=keops, metric=metric)
            P = affinity.get(X)
            list_P.append(P)

            # -- check properties of the affinity matrix --
            check_type(P, keops=keops)
            assert P.shape == (n, n), "Affinity matrix shape is incorrect"
            check_symmetry(P)
            check_marginal(P, one, dim=1, tol=tol)

        # --- check equality between torch and keops ---
        check_equality_torch_keops(list_P[0], list_P[1], K=10)
