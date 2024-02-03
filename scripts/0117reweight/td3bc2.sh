
# /home/orl/ablations-halfcheetah-medium-v2/adaptivecondition/fixed
# /home/orl/ablations-halfcheetah-medium-v2/adaptivecondition/uncond
# /home/orl/ablations-halfcheetah-medium-v2/Grid/high
# /home/orl/ablations-halfcheetah-medium-v2/Grid/low

ext=npz
for datapath in /home/orl/ablations-halfcheetah-medium-v2/low/*
do
    if [[ "$datapath" == *"$ext"* ]]; then
        bash /home/sujin/project/Augmentation-For-OfflineRL/scripts/0117reweight/halfcheetah-medium/td3_bc.sh 4 $datapath
        wait
    fi
done