from .models import ReqStatus, Requirement

allowed_transitions = {
    ReqStatus.draft: {ReqStatus.pending_review},
    ReqStatus.pending_review: {ReqStatus.feasible, ReqStatus.info_needed, ReqStatus.plan_needed, ReqStatus.infeasible},
    ReqStatus.feasible: {ReqStatus.in_dev},
    ReqStatus.in_dev: {ReqStatus.delivered},
    ReqStatus.info_needed: {ReqStatus.pending_review},
    ReqStatus.plan_needed: {ReqStatus.pending_review},
    ReqStatus.infeasible: {ReqStatus.pending_review},
    ReqStatus.delivered: set(),
}


def can_transition(frm: ReqStatus, to: ReqStatus) -> bool:
    return to in allowed_transitions.get(frm, set())


def transition(req: Requirement, to: ReqStatus, reason: str = "") -> Requirement:
    if not can_transition(req.status, to):
        raise ValueError(f"非法状态流转: {req.status.value} -> {to.value}")
    req.status = to
    if to == ReqStatus.infeasible:
        req.infeasible_reason = reason
    return req
