from sqlalchemy_dummy_data.seq import iters


class Test:
    def test__triangled(self):
        # 2d is easy to verify by comparison.
        d2 = list(iters._triangled(2, start=1, stop=3))
        expect = [(1, 1), (1, 2), (2, 2), (1, 3), (2, 3), (3, 3)]
        assert d2 == expect

        # For 3d verify uniqueness and length. Every member of the product
        for k in range(3, 7):
            d3 = list(iters._triangled(k, start=1, stop=3))
            assert len(set(item for item in d3)) == (len(d3))
            # assert n == int(4 * (3 ** (k - 1)) / 2)

    def test__squared(self):
        # This test may be slow. The results will be used lazily.
        for k in range(3, 8):
            d3 = tuple(iters._squared(k, start=1, stop=3))
            e3 = tuple(iters._triangled(k, start=1, stop=3))
            assert len(set(d3)) == len(d3)

    def test_triangled(self):
        d2 = list(iters.triangled("first", "second", "third", start=1, stop=2))
        assert len(d2) == 4
