"""
邮件发送模块
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
from config.settings import EMAIL_CONFIG


class Mailer:
    """邮件发送器"""
    
    def __init__(self, 
                 smtp_server: str = None,
                 smtp_port: int = None,
                 username: str = None,
                 password: str = None,
                 from_addr: str = None,
                 to_addr: str = None):
        self.smtp_server = smtp_server or EMAIL_CONFIG["smtp_server"]
        self.smtp_port = smtp_port or EMAIL_CONFIG["smtp_port"]
        self.username = username or EMAIL_CONFIG["username"]
        self.password = password or EMAIL_CONFIG["password"]
        self.from_addr = from_addr or EMAIL_CONFIG["from_addr"] or self.username
        self.to_addr = to_addr or EMAIL_CONFIG["to_addr"]
    
    def send(self, html_content: str, start_date: str, end_date: str, 
             attachment_path: str = None) -> bool:
        """
        发送邮件
        :param html_content: HTML 邮件正文
        :param start_date: 开始日期
        :param end_date: 结束日期
        :param attachment_path: 附件路径（可选）
        :return: 是否发送成功
        """
        if not self._validate_config():
            print("邮件配置不完整，跳过发送")
            return False
        
        try:
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = EMAIL_CONFIG["subject_template"].format(
                start_date=start_date, 
                end_date=end_date
            )
            msg['From'] = self.from_addr
            msg['To'] = self.to_addr
            
            # 添加 HTML 正文
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # 添加附件（如果提供）
            if attachment_path and os.path.exists(attachment_path):
                with open(attachment_path, 'rb') as f:
                    attachment = MIMEBase('application', 'octet-stream')
                    attachment.set_payload(f.read())
                
                encoders.encode_base64(attachment)
                filename = os.path.basename(attachment_path)
                attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{filename}"'
                )
                msg.attach(attachment)
            
            # 连接 SMTP 服务器并发送
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.from_addr, self.to_addr, msg.as_string())
            
            print(f"邮件发送成功: {self.to_addr}")
            return True
            
        except Exception as e:
            print(f"邮件发送失败: {e}")
            return False
    
    def _validate_config(self) -> bool:
        """验证邮件配置"""
        return all([
            self.smtp_server,
            self.smtp_port,
            self.username,
            self.password,
            self.to_addr
        ])


class MockMailer(Mailer):
    """模拟邮件发送器（用于测试）"""
    
    def __init__(self, *args, **kwargs):
        pass
    
    def send(self, html_content: str, start_date: str, end_date: str, 
             attachment_path: str = None) -> bool:
        """模拟发送邮件"""
        print(f"[模拟] 邮件已准备好")
        print(f"  收件人: wangmeng42@baidu.com")
        print(f"  主题: 竞品周报 {start_date} ~ {end_date}")
        print(f"  正文长度: {len(html_content)} 字符")
        if attachment_path:
            print(f"  附件: {attachment_path}")
        return True
