# encoding: utf-8
import logging
from logging import handlers
import os

LOG_TOES_PATH = "./logs/running_logs.log"

os.makedirs(os.path.dirname(LOG_TOES_PATH), exist_ok=True)
time_rota_handler = handlers.TimedRotatingFileHandler(
    filename=LOG_TOES_PATH,
    when="w0",
    interval=4,
    backupCount=12,
    encoding="utf-8")

time_rota_handler.setFormatter(
    logging.Formatter(
        fmt = '%(message)s'
    )
)

model_logger = logging.Logger(name="查看当前状态", level=logging.DEBUG)
model_logger.addHandler(time_rota_handler)