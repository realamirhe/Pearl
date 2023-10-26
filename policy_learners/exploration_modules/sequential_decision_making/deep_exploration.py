from typing import Optional

import torch

from pearl.api.action import Action
from pearl.api.action_space import ActionSpace
from pearl.api.state import SubjectiveState
from pearl.neural_networks.common.value_networks import EnsembleQValueNetwork
from pearl.policy_learners.exploration_modules.exploration_module import (
    ExplorationModule,
)
from pearl.utils.device import get_pearl_device
from torch.nn import functional as F


class DeepExploration(ExplorationModule):
    r"""An exploration strategy that follows a policy based on a randomly
    drawn value function (from its posterior distribution), an idea that was
    developed in [1, 2, 3]. The implementation is based off of [3] and uses an
    ensemble of Q-value functions.

    [1] Ian Osband, Daniel Russo, and Benjamin Van Roy, (More) efficient reinforcement
        learning via posterior sampling. Advances in Neural Information Processing
        Systems, 2013. https://arxiv.org/abs/1306.0940.
    [2] Ian Osband, Benjamin Van Roy, Daniel Russo, and Zheng Wen, Deep exploration
        via randomized value functions. Journal of Machine Learning Research, 2019.
        https://arxiv.org/abs/1703.07608.
    [3] Ian Osband, Charles Blundell, Alexander Pritzel, and Benjamin
        Vay Roy, Deep exploration via bootstrapped DQN. Advances in Neural
        Information Processing Systems, 2016. https://arxiv.org/abs/1602.04621.
    """

    def __init__(
        self,
        q_ensemble_network: EnsembleQValueNetwork,
    ) -> None:
        super(DeepExploration, self).__init__()
        self.q_ensemble_network = q_ensemble_network

    def act(
        self,
        subjective_state: SubjectiveState,
        action_space: ActionSpace,
        exploit_action: Optional[Action] = None,
        values: Optional[torch.Tensor] = None,
        action_availability_mask: Optional[torch.Tensor] = None,
        representation: Optional[torch.nn.Module] = None,
    ) -> Action:
        device = get_pearl_device()

        # (state_dim)
        subjective_state_tensor = torch.tensor(subjective_state, device=device)

        # (action_space_size x state_dim)
        states_repeated = torch.repeat_interleave(
            subjective_state_tensor.unsqueeze(0), action_space.n, dim=0  # pyre-ignore
        ).to(device)

        # (action_space_size, action_dim)
        actions = F.one_hot(torch.arange(0, action_space.n)).to(device)

        with torch.no_grad():
            q_values = self.q_ensemble_network.get_q_values(
                state_batch=states_repeated, action_batch=actions, persistent=True
            )  # this does a forward pass since all available actions are already stacked together

        return torch.argmax(q_values).view((-1)).item()

    def reset(self) -> None:  # noqa: B027
        # sample a new epistemic index (i.e., a Q-network) at the beginning of a
        # new episode for temporally consistent exploration
        self.q_ensemble_network.resample_epistemic_index()