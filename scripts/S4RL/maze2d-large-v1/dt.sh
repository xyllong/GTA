device=cuda:2
std_scale=0.0003
uniform_scale=0.0003
adv_scale=0.0001
env=maze2d-large-v1
GDA=None
max_timesteps=100000
batch_size=4096
eval_episodes=100

for s4rl_augmentation_type in 'identical' 'gaussian_noise'
do
    python corl/algorithms/dt.py --device=$device --eval_episodes=$eval_episodes --s4rl_augmentation_type=$s4rl_augmentation_type --adv_scale=$adv_scale --std_scale=$std_scale --uniform_scale=$uniform_scale --env=$env --GDA=$GDA --seed=0 --max_timesteps=$max_timesteps --batch_size=$batch_size &
    python corl/algorithms/dt.py --device=$device --eval_episodes=$eval_episodes --s4rl_augmentation_type=$s4rl_augmentation_type --adv_scale=$adv_scale --std_scale=$std_scale --uniform_scale=$uniform_scale --env=$env --GDA=$GDA --seed=1 --max_timesteps=$max_timesteps --batch_size=$batch_size &
    python corl/algorithms/dt.py --device=$device --eval_episodes=$eval_episodes --s4rl_augmentation_type=$s4rl_augmentation_type --adv_scale=$adv_scale --std_scale=$std_scale --uniform_scale=$uniform_scale --env=$env --GDA=$GDA --seed=2 --max_timesteps=$max_timesteps --batch_size=$batch_size &
    python corl/algorithms/dt.py --device=$device --eval_episodes=$eval_episodes --s4rl_augmentation_type=$s4rl_augmentation_type --adv_scale=$adv_scale --std_scale=$std_scale --uniform_scale=$uniform_scale --env=$env --GDA=$GDA --seed=3 --max_timesteps=$max_timesteps --batch_size=$batch_size &
    wait
    python corl/algorithms/dt.py --device=$device --eval_episodes=$eval_episodes --s4rl_augmentation_type=$s4rl_augmentation_type --adv_scale=$adv_scale --std_scale=$std_scale --uniform_scale=$uniform_scale --env=$env --GDA=$GDA --seed=4 --max_timesteps=$max_timesteps --batch_size=$batch_size &
    python corl/algorithms/dt.py --device=$device --eval_episodes=$eval_episodes --s4rl_augmentation_type=$s4rl_augmentation_type --adv_scale=$adv_scale --std_scale=$std_scale --uniform_scale=$uniform_scale --env=$env --GDA=$GDA --seed=5 --max_timesteps=$max_timesteps --batch_size=$batch_size &
    python corl/algorithms/dt.py --device=$device --eval_episodes=$eval_episodes --s4rl_augmentation_type=$s4rl_augmentation_type --adv_scale=$adv_scale --std_scale=$std_scale --uniform_scale=$uniform_scale --env=$env --GDA=$GDA --seed=6 --max_timesteps=$max_timesteps --batch_size=$batch_size &
    python corl/algorithms/dt.py --device=$device --eval_episodes=$eval_episodes --s4rl_augmentation_type=$s4rl_augmentation_type --adv_scale=$adv_scale --std_scale=$std_scale --uniform_scale=$uniform_scale --env=$env --GDA=$GDA --seed=7 --max_timesteps=$max_timesteps --batch_size=$batch_size &
    wait
done
