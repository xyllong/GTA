
device=cuda:3
std_scale=0.0003
uniform_scale=0.0003
adv_scale=0.0001
env=halfcheetah-medium-v2
GDA=5M-1_3x-smallmixer-50-sar-temp1_0-halfcheetah-v4
s4rl_augmentation_type=identical
datapath=results/halfcheetah-medium-v2/smallmixer_denoiser_v4/2023-12-25/23:28/5M-1_3x-smallmixer-50-sar-temp1_0.npz
batch_size=1024
max_timesteps=1000000

python corl/algorithms/generated_data_validation.py --device=$device --s4rl_augmentation_type=$s4rl_augmentation_type --adv_scale=$adv_scale --std_scale=$std_scale --uniform_scale=$uniform_scale --env=$env --GDA=$GDA --seed=0 --datapath=$datapath --batch_size=$batch_size --max_timesteps=$max_timesteps&
python corl/algorithms/generated_data_validation.py --device=$device --s4rl_augmentation_type=$s4rl_augmentation_type --adv_scale=$adv_scale --std_scale=$std_scale --uniform_scale=$uniform_scale --env=$env --GDA=$GDA --seed=1 --datapath=$datapath --batch_size=$batch_size --max_timesteps=$max_timesteps&
python corl/algorithms/generated_data_validation.py --device=$device --s4rl_augmentation_type=$s4rl_augmentation_type --adv_scale=$adv_scale --std_scale=$std_scale --uniform_scale=$uniform_scale --env=$env --GDA=$GDA --seed=2 --datapath=$datapath --batch_size=$batch_size --max_timesteps=$max_timesteps&
python corl/algorithms/generated_data_validation.py --device=$device --s4rl_augmentation_type=$s4rl_augmentation_type --adv_scale=$adv_scale --std_scale=$std_scale --uniform_scale=$uniform_scale --env=$env --GDA=$GDA --seed=3 --datapath=$datapath --batch_size=$batch_size --max_timesteps=$max_timesteps&
python corl/algorithms/generated_data_validation.py --device=$device --s4rl_augmentation_type=$s4rl_augmentation_type --adv_scale=$adv_scale --std_scale=$std_scale --uniform_scale=$uniform_scale --env=$env --GDA=$GDA --seed=4 --datapath=$datapath --batch_size=$batch_size --max_timesteps=$max_timesteps&
