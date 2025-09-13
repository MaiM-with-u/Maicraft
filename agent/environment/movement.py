import asyncio
import math
import time
import traceback
from agent.common.basic_class import Position
from utils.logger import get_logger
from agent.thinking_log import global_thinking_log

logger = get_logger("Movement")

class Movement:
    def __init__(self):
        self.position = None
        self.position_velocity = None
        self.position_speed = 0
        
        self.vertical_velocity = 0
        self.horizontal_velocity = 0
        
        self.falling = False
        self.teleported = False
        
        self.on_ground = True
        
        # self.velocity = None
        # self.speed = 0
        
        self.last_update_time = time.time()
        
        # 中断标志
        self.interrupt_flag = False
        self.interrupt_reason = ""
        
    def trigger_interrupt(self, reason: str):
        """触发中断标志"""
        self.interrupt_reason = reason
        self.interrupt_flag = True
        
    def clear_interrupt(self):
        """清除中断标志"""
        self.interrupt_reason = ""
        self.interrupt_flag = False
        
    def set_position(self, position: Position):
        if not self.position:
            self.position = position
            self.last_update_time = time.time()
            return
        
        # *计算速度
        dt = time.time() - self.last_update_time
        self.last_update_time = time.time()
        self.position_velocity = (position - self.position) / dt
        
        # *更新位置
        self.position = position
        
        # *计算速率
        self.position_speed = 0
        for i in range(3):
            self.position_speed += self.position_velocity.get_value(i) ** 2
        self.position_speed = math.sqrt(self.position_speed)

        # *计算垂直速度和水平速率
        self.vertical_velocity = self.position_velocity.get_value(1)
        self.horizontal_velocity = math.sqrt(self.position_velocity.get_value(0) ** 2 + self.position_velocity.get_value(2) ** 2)
        
        # !速度大于10,坠落
        if self.vertical_velocity < -13:
            self.falling = True
            
        # !高速移动，传送
        if self.position_speed > 30:
            self.teleported = True
    
    async def run_speed_monitor(self):
        self.check_speed_task = asyncio.create_task(self.check_speed())

            
    async def check_speed(self):
        while True:
            await asyncio.sleep(0.5)
            
            if self.falling:
                if self.on_ground:
                    global_thinking_log.add_thinking_log(f"注意！你刚刚坠落了，现已落地，当前位置：(x={self.position.get_value(0)},y={self.position.get_value(1)},z={self.position.get_value(2)})。",type = "notice")
                    # 触发中断标志
                    reason = "刚刚经历坠落，需要重新考虑行动"
                    self.trigger_interrupt(reason)
                    
                    self.falling = False
                else:
                    global_thinking_log.add_thinking_log(f"注意！你正在坠落！现在速度：{self.vertical_velocity}，当前位置：(x={self.position.get_value(0)},y={self.position.get_value(1)},z={self.position.get_value(2)})。",type = "notice")
                

                
                
            if self.teleported:
                global_thinking_log.add_thinking_log(f"注意！你刚刚被传送到了新位置，当前位置：(x={self.position.get_value(0)},y={self.position.get_value(1)},z={self.position.get_value(2)})。",type = "notice")
                
                # 触发中断标志
                reason = "刚刚经历传送，需要重新考虑行动"
                self.trigger_interrupt(reason)
                
                self.teleported = False
            
    
    def set_on_ground(self, on_ground: bool):
        self.on_ground = on_ground
    
    def show_movement_info(self):
        # logger.info("--------------------------------")
        # logger.info(f"position: {self.position}")
        # logger.info(f"position_velocity: {self.position_velocity}")
        # logger.info(f"velocity: {self.velocity}")
        logger.info(f"position_speed: {self.position_speed}")
        # logger.info(f"speed: {self.speed}")
        
    
    def __del__(self):
        """析构函数，确保停止检查速度任务"""
        try:
            self.check_speed_task.cancel()
        except:
            logger.error(f"停止检查速度任务失败: {traceback.format_exc()}")
            pass
    

global_movement = Movement()