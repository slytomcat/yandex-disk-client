#! /bin/bash
python3 Disk.py&
sleep 70
cd /home/ubuntu/yd
echo "---------------------**** LS ****-------------------"
ls
echo "---------------------**** LS ****-------------------"
sleep 10
echo "---------------------**** test ****-------------------"
bash test.sh
sleep 70