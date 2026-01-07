#!/bin/bash
cd /workspace/vidaio-subnet
source /venv/main/bin/activate
export PYTHONPATH=/workspace/vidaio-subnet:$PYTHONPATH
exec python neurons/miner.py \
  --wallet.name brunofdream \
  --wallet.hotkey sn851 \
  --subtensor.network finney \
  --netuid 85 \
  --axon.port 8091 \
  --axon.external_ip 104.188.118.187 \
  --axon.external_port 47437 \
  --logging.info
