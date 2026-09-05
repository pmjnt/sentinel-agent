from app.models.policy import PolicyPatch, PortfolioPolicy
from app.services.policy_service import apply_policy_patch


class InMemoryPolicySessionStore:
    """Keep validated portfolio policy for local, single-user sessions."""

    def __init__(self) -> None:
        self._policies: dict[str, PortfolioPolicy] = {}

    def get(self, session_id: str) -> PortfolioPolicy:
        normalized_id = self._normalize_session_id(session_id)
        return self._policies.get(normalized_id, PortfolioPolicy())

    def apply(self, session_id: str, patch: PolicyPatch) -> PortfolioPolicy:
        normalized_id = self._normalize_session_id(session_id)
        updated = apply_policy_patch(self.get(normalized_id), patch)
        self._policies[normalized_id] = updated
        return updated

    def apply_many(
        self,
        session_id: str,
        patches: tuple[PolicyPatch, ...],
    ) -> PortfolioPolicy:
        """Atomically apply ordered validated patches after a successful Agent run."""
        normalized_id = self._normalize_session_id(session_id)
        updated = self.get(normalized_id)
        for patch in patches:
            updated = apply_policy_patch(updated, patch)
        if patches:
            self._policies[normalized_id] = updated
        return updated

    def clear(self, session_id: str) -> None:
        normalized_id = self._normalize_session_id(session_id)
        self._policies.pop(normalized_id, None)

    @staticmethod
    def _normalize_session_id(session_id: str) -> str:
        normalized = session_id.strip()
        if not normalized:
            raise ValueError("Session ID must not be empty.")
        return normalized
