import datetime
import json
import os
import re
import zlib

import HMLogan
from Crypto.Cipher import AES

gdsp_type_map = {
    "0x01": "Wristlet",
    "0x02": "Heart rate",
    "0x03": "ECG",
    "0x04": "Temperature",
    "0x05": "Sport summary",
    "0x06": "Sport detail",
    "0x07": "log",
    "0x08": "RR interval",
    "0x09": "Statistics info",
    "0x0A": "AF",
    "0x0B": "AF PPG",
    "0x0C": "ALG info",
    "0x0D": "PAI",
    "0x0E": "Coaching",
    "0x0F": "HR summary",
    "0x10": "PPG",
    "0x11": "AF result",
    "0x12": "Stress",
    "0x13": "Allday stress",
    "0x1C": "data summary",
    "0x1E": "AF ACC",
    "0x20": "health summary",
    "0x21": "GPS detail",
    "0x22": "heart rate detail",
    "0x23": "Firstbeat data",
    "0x24": "Firstbeat config",
    "0x25": "SPO2",
    "0x26": "OSA process SPO2",
    "0x27": "OSA event information",
    "0x28": "ODI数据",
    "0x29": "站立数据",
    "0x2A": "ECGsummary",
    "0x2B": "York OSA事件信息",
    "0x2C": "打点数据",
    "0x2D": "固件ECG丢包标记信息",
    "0x2E": "全天腕温数据",
    "0x2F": "腕温单次测量数据",
    "0x30": "腕温80S数据",
    "0x31": "耳机听力健康相关数据",
    "0x32": "高低心率扩展协议数据",
    "0x33": "设备端设置数据",
    "0x34": "血压校准原始数据",
    "0x35": "血压校准特征数据",
    "0x36": "手动测量原始数据",
    "0x37": "手动测量结果",
    "0x38": "睡眠呼吸率数据",
    "0x39": "睡眠呼吸率事件",
    "0x3A": "静息心率",
    "0x3B": "运动效果",
    "0x3C": "行为标注离线数据采集",
    "0x3D": "运动最大心率数据",
    "0x3E": "睡眠连续血压测量结果",
    "0x3F": "今日活动同步",
    "0x40": "高低心率提醒",
    "0x41": "低血氧提醒",
    "0x42": "睡眠计划同步",
    "0x43": "身体电量",
    "0x44": "跌倒检测ACC数据",
    "0x45": "跌倒检测执行情况",
    "0x46": "运动后恢复心率",
    "0x47": "身体成分",
    "0x48": "睡眠结果",
    "0x49": "HRV",
    "0x4A": "OSA result",
    "0x4B": "Health center",
    "0x4C": "Jet lag",
    "0x50": "chip log",
    "0x51": "Duet statistic",
    "0x52": "Body composition accessories",
    "0x53": "Ambient light",
    "0x54": "EDA raw data"
}


def get_gdsp_type_form_map(type):
    hex_number = hex(int(type))
    # 格式化为 0x01 形式
    formatted_hex = hex_number[:2] + hex_number[2:].zfill(2).upper()
    return gdsp_type_map.get(formatted_hex, type) + f"({type})"


def exception_type(type):
    return type in ['44'] or type in ['打点数据']


class MyLogan(HMLogan.HuamiLogan):
    def __init__(self, file_path: str = None, key: bytes = None, iv: bytes = None):
        super().__init__(file_path, key, iv)

    def output_log(self, fp: str = None, fn: str = None, errors: str = None) -> dict:
        """
        Output formatted log file with additional processing.
        
        Args:
            fp: File path for output
            fn: File name for output
            errors: Error handling mode
        
        Returns:
            Dictionary containing parsing results and metadata
        """
        start_time = datetime.datetime.now()
        original_size = os.path.getsize(self.file_path)

        # 1. 使用更好的默认值处理
        fp = fp or os.getcwd()
        fn = fn or f'{self.file_path}_result'

        if not os.path.exists(fp):
            raise ValueError('Output path does not exist')

        # 2. 提取常量
        ERROR_LOG_PATTERN = r'Stop transfer \d+, code=(?!SUCCESS)\w+'
        FETCH_ERROR_PATTERN = r'fetchData control point:.*?, desc=(?!成功)\S+'
        SYNC_LOG_PATTERN = 'GDSP|SyncCenter|HMBaseTask|SyncTimeUseCaseImpl|ServerSyncTimeRepository|DeviceXBuilder'
        gdsp_header = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}).*?type:(\d+) MkTime\{(.*?)\}'
        IOS_GDSP_PATTERN = r"BaseJob\.swift \| GDSPDomain.*?(\S+?)\(code: (\d+)\).*?errorCode is: (\d+)\((.*?)\)"

        # 3. 将日志处理逻辑拆分为更小的函数
        def process_unformatted_data(data: bytes) -> bytes:
            if b'{"c' not in data:
                return (b'{"c":"{\\"fc\\":\\"\\",\\"l\\":\\"\\",\\"t\\":\\"\\",\\"tz\\":\\"\\",\\"m\\":\\"Format Error:'
                        + data + b'\\"}","f":4,"l":0,"n":"","i":0,"m":false}\n')
            return data

        parse_result = self.parse_log()

        # 4. 使用列表推导式优化性能
        parse_result['unformat_data'] = [
            process_unformatted_data(log.decode(encoding="utf-8", errors="ignore").encode())
            for log in parse_result['unformat_data']
        ]

        unformat_data = b''.join(parse_result['unformat_data'])
        if not unformat_data:
            return {'status': False, 'message': '非Logan日志'}

        # 5. 使用生成器优化内存使用
        def parse_log_entries():
            for entry in re.compile(b'\{.*?"c":.*?\}\n').finditer(unformat_data):
                try:
                    log_entry = entry.group().decode(encoding="utf-8", errors="ignore")
                    log_json = json.loads(log_entry) if errors != 'ignore' else self._safe_json_load(log_entry)
                    yield self.format_log(log_json)[0]
                except Exception as e:
                    if errors == 'ignore':
                        continue
                    raise

        # 6. 使用上下文管理器和更清晰的文件写入逻辑
        output_path = os.path.join(fp, fn)
        with open(output_path, 'w') as f:
            # 写入grep使用说明
            self._write_header(f, output_path)

            add_info = []
            errors_info = []
            format_errors = set()

            # 写入主体日志内容
            for log_entry in parse_log_entries():
                f.write(f"{log_entry}\n")

                if re.search(SYNC_LOG_PATTERN, log_entry):
                    add_info.append(log_entry)
                if re.search(ERROR_LOG_PATTERN, log_entry):
                    pattern = r"Stop transfer (\d+), code=(\w+)"
                    match = re.search(pattern, log_entry)
                    format_errors.add(
                        frozenset(
                            {"type": get_gdsp_type_form_map(match.group(1)), "code": match.group(2),
                             "error_type": "GDSP_Header"}.items()))
                    errors_info.append(log_entry)
                if re.search(FETCH_ERROR_PATTERN, log_entry):
                    pattern = r'fetchData control point:.*?, desc=(\S+)'
                    match = re.search(pattern, log_entry)
                    format_errors.add(
                        frozenset({"code": match.group(1), "error_type": "GDSP_Data"}.items()))
                    errors_info.append(log_entry)
                if match := re.search(IOS_GDSP_PATTERN, log_entry):
                    sync_name = match.group(1)  # 提取同步名称
                    sync_code = match.group(2)  # 提取 code 数值
                    error_code = match.group(3)  # 提取 errorCode 数值
                    error_message = match.group(4)  # 提取错误信息
                    format_errors.add(
                        frozenset({"type": sync_name, "error_type": "GDSP_Data", "code": error_message}.items()))
                    errors_info.append(log_entry)
                if match := re.search(gdsp_header, log_entry):
                    timestamp_str = match.group(1)  # '2025-02-21 08:07:00.303'
                    type_value = get_gdsp_type_form_map(match.group(2))  # '19'
                    mk_time_str = match.group(3)  # 'year=2025, month=2, day=20, hour=0, minute=0, second=0, tz=28'

                    # 将日志中的时间转换为 datetime 对象
                    timestamp = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
                    # 从 mk_time_str 中提取出日期和时间信息
                    mk_time_values = {k: int(v) for k, v in re.findall(r'(\w+)=(\d+)', mk_time_str)}
                    mk_time = datetime.datetime(mk_time_values['year'], mk_time_values['month'], mk_time_values['day'],
                                                mk_time_values['hour'], mk_time_values['minute'],
                                                mk_time_values['second'])

                    if mk_time >= timestamp + datetime.timedelta(hours=1) and not exception_type(type_value):
                        errors_info.append(
                            f"type:{type_value} 未来时间戳，无法同步 timestamp={timestamp} mk_time={mk_time}")
                        format_errors.add(frozenset(
                            {"type": type_value, "error_type": "MkTime_1h_new"}.items()))
                    elif mk_time <= timestamp - datetime.timedelta(weeks=4):
                        errors_info.append(
                            f"type:{type_value} 同步了过去一个月的数据，需要关注 timestamp={timestamp} mk_time={mk_time}")
                        format_errors.add(frozenset(
                            {"type": type_value, "error_type": "MkTime_1m_old"}.items()))

                else:
                    pass

            # 写入过滤的日志
            self._write_filtered_logs(f, add_info, errors_info)

            # 在文件末尾写入统计信息
            processing_time = (datetime.datetime.now() - start_time).total_seconds()
            self._write_statistics(f, original_size, processing_time)

        # 7. 使用字典字面量简化代码
        parse_result.update({
            'app_info': {
                'device_name': self.device_name,
                'user_id': self.user_id,
                'system_version': self.system_version,
                'app_name': self.app_name,
                'platform': self.platform,
                'version_name': self.version_name,
                'version_code': self.version_code,
                'time_zone': self.time_zone
            },
            'out_file': output_path,
            'format_errors': json.dumps([dict(item) for item in format_errors], ensure_ascii=False)
        })
        return parse_result

    def parse_log(self):
        """Parse encrypted log file and return decrypted content."""
        result = {
            'status': None,
            'unformat_data': [],
            'message': None
        }

        try:
            with open(self.file_path, 'rb') as f:
                content = f.read()

            file_length = len(content)
            cursor = 0

            while cursor < file_length:
                # 检查标志位和长度
                if content[cursor:cursor + 1] != b'\x01':
                    cursor += 1
                    continue

                cursor += 1
                if cursor + 4 > file_length:
                    break

                # 读取数据长度
                length_bytes = content[cursor:cursor + 4]
                _length = int.from_bytes(length_bytes, byteorder='big')
                cursor += 4

                if not _length or cursor + _length > file_length:
                    continue

                # 读取数据块
                data_end = cursor + _length
                text = content[cursor:data_end]

                try:
                    # 解密数据
                    cryptor = AES.new(self.key, AES.MODE_CBC, self.iv)
                    plain_text = cryptor.decrypt(text)

                    # 解压数据
                    decompressor = zlib.decompressobj(zlib.MAX_WBITS | 16)
                    uncompress_data = decompressor.decompress(plain_text)
                    result['unformat_data'].append(uncompress_data)

                except Exception as e:
                    result['unformat_data'].append(
                        b'{"c":"{\\"fc\\":\\"\\",\\"l\\":\\"\\",\\"t\\":\\"\\",\\"tz\\":\\"\\",\\"m\\":\\"Error: '
                        + str(e).encode() + b'\\"}","f":4,"l":0,"n":"","i":0,"m":false}\n'
                    )

                cursor = data_end
                # 检查下一个字节是否为分隔符
                if cursor < file_length and content[cursor:cursor + 1] == b'\x00':
                    cursor += 1

            if result['unformat_data']:
                result['status'] = True
                result['message'] = '日志解析成功'

        except Exception as e:
            result['status'] = False
            result['message'] = f'日志解析失败: {str(e)}'

        return result

    @staticmethod
    def _safe_json_load(log_entry: str) -> dict:
        """Safely load JSON with error handling."""
        try:
            return json.loads(log_entry)
        except json.JSONDecodeError:
            return {
                'c': json.dumps({
                    'fc': '', 'l': '', 't': '', 'm': f'JSONDecodeError：{log_entry}',
                    'cd': '', 'time': '', 'tz': ''
                }),
                'f': 4, 'l': 0, 'n': '', 'i': 0, 'm': False
            }

    @staticmethod
    def _write_header(file, output_path: str):
        """Write header information to log file."""
        file.write(f"cat '{output_path}'\n\n")
        file.write("""grep 使用说明:
-i：在搜索的时候忽略大小写
-n：显示结果所在行号
-c：统计匹配到的行数，注意，是匹配到的总行数，不是匹配到的次数
-o：只显示符合条件的字符串，但是不整行显示，每个符合条件的字符串单独显示一行
-v：输出不带关键字的行（反向查询，反向匹配）
-w：匹配整个单词，如果是字符串中包含这个单词，则不作匹配
-Ax：在输出的时候包含结果所在行之后的指定行数，这里指之后的x行，A：after
-Bx：在输出的时候包含结果所在行之前的指定行数，这里指之前的x行，B：before
-Cx：在输出的时候包含结果所在行之前和之后的指定行数，这里指之前和之后的x行，C：context
-e：实现多个选项的匹配，逻辑or关系\n\n""")

    @staticmethod
    def _write_statistics(file, original_size: int, processing_time: float):
        """
        Write statistics information to file.
        
        Args:
            file: File object to write to
            original_size: Original file size in bytes
            processing_time: Time taken to process the file in seconds
        """

        def format_size(size_in_bytes: int) -> str:
            """Convert bytes to human readable format."""
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_in_bytes < 1024:
                    return f"{size_in_bytes:.2f} {unit}"
                size_in_bytes /= 1024
            return f"{size_in_bytes:.2f} TB"

        file.write("\n\n*********************************************文件统计信息******************\n")
        file.write(f"\n文件大小: {format_size(original_size)}")
        file.write(f"\n处理用时: {processing_time:.2f} 秒\n")

    @staticmethod
    def _write_filtered_logs(file, add_info: list, errors_info: list):
        """Write filtered logs to file."""
        file.write("\n\n\n\n*********************************************同步中心日志过滤******************\n\n")
        file.writelines(f"{log}\n" for log in add_info)

        file.write("\n\n\n\n*********************************************ERROR INFO******************\n\n")
        file.writelines(f"{log}\n" for log in errors_info)
