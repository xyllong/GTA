sh scripts/S4RL/halfcheetah-medium/bc_100.sh &
sh scripts/S4RL/halfcheetah-medium-expert/bc_100.sh &
sh scripts/S4RL/halfcheetah-medium-replay/bc_100.sh &
sh scripts/S4RL/halfcheetah-random/bc_100.sh &
wait

sh scripts/S4RL/hopper-medium/bc_100.sh &
sh scripts/S4RL/hopper-medium-expert/bc_100.sh &
sh scripts/S4RL/hopper-medium-replay/bc_100.sh &
sh scripts/S4RL/hopper-random/bc_100.sh &
wait

sh scripts/S4RL/walker2d-medium/bc_100.sh &
sh scripts/S4RL/walker2d-medium-expert/bc_100.sh &
sh scripts/S4RL/walker2d-medium-replay/bc_100.sh &
sh scripts/S4RL/walker2d-random/bc_100.sh &
wait

sh scripts/S4RL/maze2d-umaze-v1/bc_100.sh &
sh scripts/S4RL/maze2d-medium-v1/bc_100.sh &
sh scripts/S4RL/maze2d-large-v1/bc_100.sh &
wait
