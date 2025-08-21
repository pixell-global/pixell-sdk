from pixell.intent.policy import IntentPolicy
from pixell.intent.rate_limit import RateLimiter


def test_policy_allow_list():
    policy = IntentPolicy(allowed={"a", "b"})
    assert policy.is_allowed("a")
    assert not policy.is_allowed("c")


def test_rate_limiter_window():
    limiter = RateLimiter(max_calls=2, per_seconds=60)
    session = "s1"
    assert limiter.allow(session, "do")
    assert limiter.allow(session, "do")
    assert not limiter.allow(session, "do") 