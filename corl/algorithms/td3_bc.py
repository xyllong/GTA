# source: https://github.com/sfujim/TD3_BC
# https://arxiv.org/pdf/2106.06860.pdf
import copy
import os
import random
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import d4rl
import gym
import numpy as np
import pyrallis
import torch
import torch.nn as nn
import torch.nn.functional as F
import wandb
import pyrootutils

path = pyrootutils.find_root(search_from = __file__, indicator=".aug-project-root")
pyrootutils.set_root(path = path,
                     project_root_env_var = True,
                     dotenv = True,
                     pythonpath = True)

from corl.shared.buffer import prepare_replay_buffer, RewardNormalizer, StateNormalizer, DiffusionConfig
from corl.shared.utils  import wandb_init, set_seed, wrap_env, soft_update, compute_mean_std, normalize_states, eval_actor, get_saved_dataset, get_generated_dataset, merge_dictionary, get_dataset
from corl.shared.validation import validate

TensorBatch = List[torch.Tensor]
os.environ["WANDB_MODE"] = "online"


@dataclass
class TrainConfig:
    # Experiment
    device: str = "cuda:3"
    s4rl_augmentation_type: str = 'identical'
    std_scale: float = 0.0003
    uniform_scale: float = 0.0003
    adv_scale: float = 0.0001
    iteration: int = 2
    diffusion: DiffusionConfig = field(default_factory=DiffusionConfig)
    env: str = "halfcheetah-medium-expert-v2"  # OpenAI gym environment name
    seed: int = 5  # Sets Gym, PyTorch and Numpy seeds
    GDA: str = 'GTA' # "gda only" 'gda with original' None
    data_mixture_type: str = 'mixed'
    GDA_id: str = None
    
    # Wandb logging
    project: str = env
    group: str = "TD3_BC-D4RL"
    name: str = "TD3_BC"
    diffusion_horizon: int = 31
    diffusion_backbone: str = 'mixer' # 'mixer', 'temporal'
    
    conditioned: bool = False
    data_volume: int = 5e6
    generation_type: str = 's' # 's,a' 's,a,r'
    guidance_temperature: float = 1.2
    guidance_target_multiple: float = 2

    step: int = 1000000 # Generated Data Augmentation 모델 학습 step 수

    eval_freq: int = int(5e3)  # How often (time steps) we evaluate
    val_freq: int = int(1e5) # Measuring Q Overestimation
    n_episodes: int = 10  # How many episodes run during evaluation
    max_timesteps: int = int(1e6)  # Max time steps to run environment
    checkpoints_path: Optional[str] = "checkpoints"
    save_checkpoints: bool = True  # Save model checkpoints
    log_every: int = 1000
    load_model: str = ""  # Model load file name, "" doesn't load
    # TD3
    buffer_size: int = 10_000_000  # Replay buffer size
    batch_size: int = 256  # Batch size for all networks
    discount: float = 0.99  # Discount factor
    expl_noise: float = 0.1  # Std of Gaussian exploration noise
    tau: float = 0.005  # Target network update rate
    policy_noise: float = 0.2  # Noise added to target actor during critic update
    noise_clip: float = 0.5  # Range to clip target actor noise
    policy_freq: int = 2  # Frequency of delayed actor updates
    # TD3 + BC
    alpha: float = 2.5  # Coefficient for Q function in actor loss
    normalize: bool = True  # Normalize states
    normalize_reward: bool = False  # Normalize reward

    # Diffusion config
    # Network size
    network_width: int = 256
    network_depth: int = 2
    
    datapath: str = None

    def __post_init__(self):
        self.name = f"{self.name}-{self.env}-{self.s4rl_augmentation_type}-{str(uuid.uuid4())[:4]}"
        if self.checkpoints_path is not None:
            self.checkpoints_path = os.path.join(self.checkpoints_path, self.name)
        if self.s4rl_augmentation_type == 'identical':
            self.iteration = 1
        if self.GDA is None:
            self.diffusion_horizon = None
            self.diffusion_backbone = None
            self.conditioned = None
            self.data_volume = None
            self.generation_type = None
            self.guidance_temperature = None
            self.guidance_target_multiple = None
        if (self.datapath is not None) and (self.datapath != 'None'):
            self.GDA = self.datapath.split("/")[-1].split(".")[0]
            if self.GDA_id is not None:
                self.GDA = self.GDA + f'_{self.GDA_id}'
            if self.data_mixture_type is not None:
                self.GDA = self.GDA + f'_{self.data_mixture_type}'




class Actor(nn.Module):
    def __init__(self, state_dim: int, action_dim: int, max_action: float, hidden_dim: int = 256, n_hidden: int = 2):
        super(Actor, self).__init__()

        layers = [nn.Linear(state_dim, hidden_dim), nn.ReLU()]
        for _ in range(n_hidden - 1):
            layers.append(nn.Linear(hidden_dim, hidden_dim))
            layers.append(nn.ReLU())
        layers.append(nn.Linear(hidden_dim, action_dim))
        layers.append(nn.Tanh())
        self.net = nn.Sequential(*layers)

        self.max_action = max_action

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        return self.max_action * self.net(state)

    @torch.no_grad()
    def act(self, state: np.ndarray, device: str = "cpu") -> np.ndarray:
        state = torch.tensor(state.reshape(1, -1), device=device, dtype=torch.float32)
        return self(state).cpu().data.numpy().flatten()
    
    @torch.no_grad()
    def get_action_array(self, state: torch.tensor) -> torch.tensor:
        return self(state)


class Critic(nn.Module):
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 256, n_hidden: int = 2):
        super(Critic, self).__init__()

        layers = [nn.Linear(state_dim + action_dim, hidden_dim), nn.ReLU()]
        for _ in range(n_hidden - 1):
            layers.append(nn.Linear(hidden_dim, hidden_dim))
            layers.append(nn.ReLU())
        layers.append(nn.Linear(hidden_dim, 1))
        self.net = nn.Sequential(*layers)

    def forward(self, state: torch.Tensor, action: torch.Tensor) -> torch.Tensor:
        sa = torch.cat([state, action], 1)
        return self.net(sa)


class TD3_BC:  # noqa
    def __init__(
            self,
            max_action: float,
            actor: nn.Module,
            actor_optimizer: torch.optim.Optimizer,
            critic_1: nn.Module,
            critic_1_optimizer: torch.optim.Optimizer,
            critic_2: nn.Module,
            critic_2_optimizer: torch.optim.Optimizer,
            discount: float = 0.99,
            tau: float = 0.005,
            policy_noise: float = 0.2,
            noise_clip: float = 0.5,
            policy_freq: int = 2,
            alpha: float = 2.5,
            device: str = "cpu",
    ):
        self.actor = actor
        self.actor_target = copy.deepcopy(actor)
        self.actor_optimizer = actor_optimizer
        self.critic_1 = critic_1
        self.critic_1_target = copy.deepcopy(critic_1)
        self.critic_1_optimizer = critic_1_optimizer
        self.critic_2 = critic_2
        self.critic_2_target = copy.deepcopy(critic_2)
        self.critic_2_optimizer = critic_2_optimizer

        self.max_action = max_action
        self.discount = discount
        self.tau = tau
        self.policy_noise = policy_noise
        self.noise_clip = noise_clip
        self.policy_freq = policy_freq
        self.alpha = alpha

        self.total_it = 0
        self.device = device

    def train(self, batch: TensorBatch) -> Dict[str, float]:
        log_dict = {}
        self.total_it += 1

        state, action, reward, next_state, done = batch
        not_done = 1 - done

        ## state augmentation이 두번 일어나야 되는걸

        with torch.no_grad():
            # Select action according to actor and add clipped noise
            noise = (torch.randn_like(action) * self.policy_noise).clamp(
                -self.noise_clip, self.noise_clip
            )

            next_action = (self.actor_target(next_state) + noise).clamp(
                -self.max_action, self.max_action
            )

            # Compute the target Q value
            target_q1 = self.critic_1_target(next_state, next_action)
            target_q2 = self.critic_2_target(next_state, next_action)
            target_q = torch.min(target_q1, target_q2)
            target_q = reward + not_done * self.discount * target_q

        # Get current Q estimates
        current_q1 = self.critic_1(state, action)
        current_q2 = self.critic_2(state, action)

        # Compute critic loss
        critic_loss = F.mse_loss(current_q1, target_q) + F.mse_loss(current_q2, target_q)
        log_dict["critic_loss"] = critic_loss.item()
        # Optimize the critic
        self.critic_1_optimizer.zero_grad()
        self.critic_2_optimizer.zero_grad()
        critic_loss.backward()
        self.critic_1_optimizer.step()
        self.critic_2_optimizer.step()

        # Delayed actor updates
        if self.total_it % self.policy_freq == 0:
            # Compute actor loss
            pi = self.actor(state)
            q = self.critic_1(state, pi)
            lmbda = self.alpha / q.abs().mean().detach()

            actor_loss = -lmbda * q.mean() + F.mse_loss(pi, action)
            log_dict["actor_loss"] = actor_loss.item()
            # Optimize the actor
            self.actor_optimizer.zero_grad()
            actor_loss.backward()
            self.actor_optimizer.step()

            # Update the frozen target models
            soft_update(self.critic_1_target, self.critic_1, self.tau)
            soft_update(self.critic_2_target, self.critic_2, self.tau)
            soft_update(self.actor_target, self.actor, self.tau)

        return log_dict

    def state_dict(self) -> Dict[str, Any]:
        return {
            "critic_1": self.critic_1.state_dict(),
            "critic_1_optimizer": self.critic_1_optimizer.state_dict(),
            "critic_2": self.critic_2.state_dict(),
            "critic_2_optimizer": self.critic_2_optimizer.state_dict(),
            "actor": self.actor.state_dict(),
            "actor_optimizer": self.actor_optimizer.state_dict(),
            "total_it": self.total_it,
        }

    def load_state_dict(self, state_dict: Dict[str, Any]):
        self.critic_1.load_state_dict(state_dict["critic_1"])
        self.critic_1_optimizer.load_state_dict(state_dict["critic_1_optimizer"])
        self.critic_1_target = copy.deepcopy(self.critic_1)

        self.critic_2.load_state_dict(state_dict["critic_2"])
        self.critic_2_optimizer.load_state_dict(state_dict["critic_2_optimizer"])
        self.critic_2_target = copy.deepcopy(self.critic_2)

        self.actor.load_state_dict(state_dict["actor"])
        self.actor_optimizer.load_state_dict(state_dict["actor_optimizer"])
        self.actor_target = copy.deepcopy(self.actor)

        self.total_it = state_dict["total_it"]


@pyrallis.wrap()
def train(config: TrainConfig):
    if config.checkpoints_path is not None:
        print(f"Checkpoints path: {config.checkpoints_path}")
        os.makedirs(config.checkpoints_path, exist_ok=True)
    config.project = config.env
    env = gym.make(config.env)

    state_dim = env.observation_space.shape[0]
    action_dim = env.action_space.shape[0]

    ##### LOADING DATASET #####
    dataset, metadata = get_dataset(config)
    trajectory_data = np.load(f'./data/{config.env}.pkl', allow_pickle=True)
    for k, v in metadata.items():
        setattr(config, k, v)

    if config.normalize:
        state_mean, state_std = compute_mean_std(dataset["observations"], eps=1e-3)
    else:
        state_mean, state_std = 0, 1
    env = wrap_env(env, state_mean=state_mean, state_std=state_std)
    replay_buffer = prepare_replay_buffer(
        state_dim=state_dim,
        action_dim=action_dim,
        buffer_size=config.buffer_size,
        dataset=dataset,
        env_name=config.env,
        device=config.device,
        s4rl_augmentation_type=config.s4rl_augmentation_type,
        std_scale=config.std_scale, 
        uniform_scale=config.uniform_scale, 
        adv_scale=config.adv_scale, 
        reward_normalizer=RewardNormalizer(dataset, config.env) if config.normalize_reward else None,
        state_normalizer=StateNormalizer(state_mean, state_std),
        diffusion_config=config.diffusion,
    )

    max_action = float(env.action_space.high[0])

    # Set seeds
    seed = config.seed
    set_seed(seed, env)

    actor = Actor(
        state_dim, action_dim, max_action, hidden_dim=config.network_width, n_hidden=config.network_depth).to(
        config.device)
    actor_optimizer = torch.optim.Adam(actor.parameters(), lr=3e-4)

    critic_1 = Critic(
        state_dim, action_dim, hidden_dim=config.network_width, n_hidden=config.network_depth).to(config.device)
    critic_1_optimizer = torch.optim.Adam(critic_1.parameters(), lr=3e-4)
    critic_2 = Critic(
        state_dim, action_dim, hidden_dim=config.network_width, n_hidden=config.network_depth).to(config.device)
    critic_2_optimizer = torch.optim.Adam(critic_2.parameters(), lr=3e-4)

    kwargs = {
        "max_action": max_action,
        "actor": actor,
        "actor_optimizer": actor_optimizer,
        "critic_1": critic_1,
        "critic_1_optimizer": critic_1_optimizer,
        "critic_2": critic_2,
        "critic_2_optimizer": critic_2_optimizer,
        "discount": config.discount,
        "tau": config.tau,
        "device": config.device,
        # TD3
        "policy_noise": config.policy_noise * max_action,
        "noise_clip": config.noise_clip * max_action,
        "policy_freq": config.policy_freq,
        # TD3 + BC
        "alpha": config.alpha,
    }

    print("---------------------------------------")
    print(f"Training TD3 + BC, Env: {config.env}, Seed: {seed}")
    print("---------------------------------------")

    # Initialize actor
    trainer = TD3_BC(**kwargs)

    if config.load_model != "":
        policy_file = Path(config.load_model)
        trainer.load_state_dict(torch.load(policy_file))
        actor = trainer.actor

    wandb_init(vars(config))

    evaluations = []
    for t in range(int(config.max_timesteps)):
        batch = replay_buffer.sample(config.batch_size, q_function=critic_1, iteration=config.iteration )
        batch = [b.to(config.device) for b in batch]
        log_dict = trainer.train(batch)

        if t % config.log_every == 0:
            wandb.log(log_dict, step=trainer.total_it)

        # Evaluate episode
        if t % config.eval_freq == 0 or t == config.max_timesteps - 1:
            print(f"Time steps: {t + 1}")
            eval_scores = eval_actor(
                env,
                actor,
                device=config.device,
                n_episodes=config.n_episodes,
                seed=config.seed,
            )
            eval_score = eval_scores.mean()
            normalized_eval_score = env.get_normalized_score(eval_score) * 100.0
            evaluations.append(normalized_eval_score)
            print("---------------------------------------")
            print(
                f"Evaluation over {config.n_episodes} episodes: "
                f"{eval_score:.3f} , D4RL score: {normalized_eval_score:.3f}"
            )
            print("---------------------------------------")
            log_dict = {"d4rl_normalized_score": normalized_eval_score,
                        "result/d4rl_normalized_score": normalized_eval_score}
            wandb.log(log_dict)
            
        if (config.val_freq != 0) and (t % config.val_freq == 0 or t == config.max_timesteps - 1):
            
            q_gap, bias = validate(trajectory_data, [critic_1, critic_2], actor, config.discount, config.device)

            print("---------------------------------------")
            print(
                f"Q gap: {q_gap.mean():.3f}, MC bias: {bias.mean():.3f} "
            )
            print("---------------------------------------")

            wandb.log({
                'Q gap mean': q_gap.mean(),
                'Q gap std': q_gap.std(),
                'MC bias mean': bias.mean(),
                'MC bias std': bias.std()
                },
                step=trainer.total_it
            )

            wandb.log(log_dict, step=trainer.total_it)
    
    config.evaluations = evaluations
    if config.checkpoints_path is not None:
        print(f"Checkpoints path: {config.checkpoints_path}")
        with open(os.path.join(config.checkpoints_path, "config.yaml"), "w") as f:
            pyrallis.dump(config, f)
        np.save(os.path.join(config.checkpoints_path, f"evaluation_results.npy") ,np.array(evaluations))
    if config.checkpoints_path is not None and config.save_checkpoints:
        torch.save(
            trainer.state_dict(),
            os.path.join(config.checkpoints_path, f"checkpoint_{t}.pt"),
        )

    return evaluations


if __name__ == "__main__":
    train()
