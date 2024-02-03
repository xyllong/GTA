
config_name="smallmixer_denoiser_v4.yaml"
group_nm="smallmixer_denoiser_v4"

env_name="walker2d"
dataset_type="medium-expert"
CUDA_VISIBLE_DEVICES="0,1,2,3" \
accelerate launch \
--multi_gpu \
--main_process_port=37117 ./src/diffusion/train_diffuser.py \
--dataset="${env_name}-${dataset_type}-v2" \
--config_name="${config_name}" \
--wandb_project="synther_${env_name}" \
--wandb_group="${group_nm}-${dataset_type}" 

wait