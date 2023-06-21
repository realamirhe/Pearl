from typing import Callable, List

import matplotlib.pyplot as plt

from pearl.api.agent import Agent
from pearl.api.environment import Environment
from pearl.api.reward import Value
from pearl.utils.plots import fontsize_for


def online_learning_to_png_graph(
    agent: Agent,
    env: Environment,
    filename="returns.png",
    number_of_episodes=1000,
    learn_after_episode=False,
    dynamic_size=False,
) -> None:
    """
    Runs online learning and generates a PNG graph of the returns.

    Args:
        agent (Agent): the agent.
        env (Environment): the environment.
        filename (str, optional): the filename to save to. Defaults to "returns.png".
        number_of_episodes (int, optional): the number of episodes to run. Defaults to 1000.
    """

    returns = online_learning_returns(
        agent, env, number_of_episodes, learn_after_episode, dynamic_size
    )

    if filename is not None:
        title = f"{str(agent)} on {str(env)}"
        plt.plot(returns)
        plt.title(title, fontsize=fontsize_for(title))
        plt.xlabel("Episode")
        plt.ylabel("Return")
        plt.savefig(filename)
        plt.close()


def online_learning_returns(
    agent: Agent,
    env: Environment,
    number_of_episodes: int = 1000,
    learn_after_episode: bool = False,
    dynamic_size: bool = False,
) -> List[Value]:
    returns = []
    online_learning(
        agent,
        env,
        number_of_episodes=number_of_episodes,
        learn_after_episode=learn_after_episode,
        process_return=returns.append,
        dynamic_size=dynamic_size,
    )
    return returns


def online_learning(
    agent: Agent,
    env: Environment,
    number_of_episodes: int = 1000,
    learn_after_episode: bool = False,
    process_return: Callable[[Value], None] = lambda g: None,
    dynamic_size: bool = False,
):
    """
    Performs online learning for a number of episodes.

    Args:
        agent (Agent): the agent.
        env (Environment): the environmnent.
        number_of_episodes (int, optional): the number of episodes to run. Defaults to 1000.
        learn_after_episode (bool, optional): asks the agent to only learn after every episode. Defaults to False.
        process_return (Callable[[Value], None], optional): a callable for processing the returns of the episodes. Defaults to no-op.
        dynamic_size (bool, optional): if True, the size of the each learning batch is equal to buffer length. Defaults to False.
    """
    for _ in range(number_of_episodes):
        g = episode_return(
            agent,
            env,
            learn=True,
            exploit=False,
            learn_after_episode=learn_after_episode,
            dynamic_size=dynamic_size,
        )
        process_return(g)


def episode_return(
    agent: Agent,
    env: Environment,
    learn: bool = False,
    exploit: bool = True,
    learn_after_episode: bool = False,
    dynamic_size: bool = False,
):
    """
    Runs one episode and returns the total reward (return).

    Args:
        agent (Agent): the agent.
        env (Environment): the environment.
        learn (bool, optional): Runs `agent.learn()` after every step. Defaults to False.
        exploit (bool, optional): asks the agent to only exploit. Defaults to False.
        learn_after_episode (bool, optional): asks the agent to only learn after every episode. Defaults to False.
        dynamic_size (bool, optional): if True, the size of the each learning batch is equal to buffer length. Defaults to False.

    Returns:
        Value: the return of the episode.
    """
    g = 0
    observation, action_space = env.reset()
    agent.reset(observation, action_space)
    done = False
    step = 1
    while not done:
        action = agent.act(exploit=exploit)
        action_result = env.step(action)
        g += action_result.reward
        agent.observe(action_result)
        if learn and not learn_after_episode:
            agent.learn(dynamic_size=dynamic_size)
        done = action_result.done
        step += 1

    if learn and learn_after_episode:
        if agent.policy_learner.batch_size > step - 1:
            # if we dont set batch_size, learn will do nothing
            agent.learn(batch_size=step - 1, dynamic_size=dynamic_size)
        else:
            agent.learn(dynamic_size=dynamic_size)

    return g
