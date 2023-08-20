from sqlalchemy_dummy_data.seq import iters


class Test:
    def test_triangle_iter(self):
        # 2d is easy to verify by comparison.
        d2 = list(iters.triangled(range(1, 4), range(1, 4)))
        assert d2 == [(1, 1), (2, 1), (2, 2), (3, 1), (3, 2), (3, 3)]

        # For 3d verify uniqueness and length. Every member of the product
        for k in range(3, 7):
            coproduct = (range(1, 4) for _ in range(k))
            d3 = list(iters.triangled(*coproduct))
            assert len(set(item for item in d3)) == (n := len(d3))
            assert n == int(4 * (3 ** (k - 1)) / 2)

    def test_squares(self):
        # This test may be slow. The results will be used lazily.
        for k in range(2, 8):
            coproduct = (range(1, 4) for _ in range(k))
            d3 = tuple(iters.squared(*coproduct))
            assert len(set(d3)) == 3**k == len(d3)
