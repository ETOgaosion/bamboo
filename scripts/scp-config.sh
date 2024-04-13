
scp scripts/run-project-pactum.sh aws-test-0:/home/ubuntu/project/bamboo/scripts/run-project-pactum-localhost.sh;
scp project_pactum/external/deepspeed/deepspeed/runtime/pipe/engine.py aws-test-0:/home/ubuntu/project/bamboo/project_pactum/external/deepspeed/deepspeed/runtime/pipe/engine.py;
for i in $(seq 1 7);
do
    scp scripts/run-project-pactum.sh aws-test-$i:/home/ubuntu/project/bamboo/scripts/run-project-pactum.sh;
    scp project_pactum/external/deepspeed/deepspeed/runtime/pipe/engine.py aws-test-$i:/home/ubuntu/project/bamboo/project_pactum/external/deepspeed/deepspeed/runtime/pipe/engine.py;
done
