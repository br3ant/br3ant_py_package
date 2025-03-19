import os

from baseopensdk import BaseClient
from baseopensdk.api.base.v1 import *
from baseopensdk.api.drive.v1 import *

from .feishu_token import FeishuToken


class FeishuDocClient:
    def __init__(self, token: FeishuToken):
        self.client = BaseClient.builder() \
            .app_token(token.app_token) \
            .personal_base_token(token.personal_token) \
            .build()
        self.token = token

    def upload(self, table_id, record_id, field_name, file_path, remove=False):
        file_path = os.path.abspath(file_path)
        file_name = os.path.basename(file_path)

        # 上传图片到 Drive 获取 file_token
        request = UploadAllMediaRequest.builder() \
            .request_body(UploadAllMediaRequestBody.builder()
                          .file_name(file_name)
                          .parent_type("bitable_file")
                          .parent_node(self.token.app_token)
                          .size(os.path.getsize(file_path))
                          .file(open(file_path, 'rb'))
                          .build()) \
            .build()
        response: UploadAllMediaResponse = self.client.drive.v1.media.upload_all(request)
        print(f"上传文件 success! code = {response.code} msg = {response.msg}")

        file_token = response.data.file_token

        if file_token:
            # 更新 file_token 到附件字段
            request = UpdateAppTableRecordRequest.builder() \
                .table_id(table_id) \
                .record_id(record_id) \
                .request_body(AppTableRecord.builder()
                              .fields({field_name: [{"file_token": file_token}]})
                              .build()) \
                .build()
            response: UpdateAppTableRecordResponse = self.client.base.v1.app_table_record.update(request)
            print(f"更新附件字段 success! code = {response.code} msg = {response.msg}")

            if remove and response.code == 0:
                print('上传成功，删除文件')
                os.remove(file_path)

    def download(self, file_token, file_path):
        # 保存文件到本地
        with open(file_path, "wb") as f:
            f.write(self.download_stream(file_token).read())

    def download_stream(self, file_token):
        # 构造请求对象
        request = DownloadMediaRequest.builder() \
            .file_token(file_token) \
            .build()

        # 发起请求
        response = self.client.drive.v1.media.download(request)

        return response.file

    # 读取指定条数的纪录
    def read(self, table_id, page_size=100, read_all=True):

        page_token = ''

        def _read():
            # 遍历记录
            list_record_request = ListAppTableRecordRequest.builder() \
                .page_size(page_size) \
                .table_id(table_id) \
                .page_token(page_token) \
                .build()

            list_record_response = self.client.base.v1.app_table_record.list(list_record_request)
            print(f"read success! code = {list_record_response.code} msg = {list_record_response.msg}")

            return list_record_response.data if list_record_response.success() else None

        while True:
            data = _read()
            yield from getattr(data, 'items', []) or []
            has_more = getattr(data, 'has_more', False)
            page_token = getattr(data, 'page_token', '')

            if not has_more or not read_all or not page_token:
                return

    # 根据条件查找纪录
    def find(self, table_id, predicate):
        list_record_request = ListAppTableRecordRequest.builder() \
            .page_size(100) \
            .table_id(table_id) \
            .filter(predicate) \
            .build()

        list_record_response = self.client.base.v1.app_table_record.list(list_record_request)
        print(f"find end! code: {list_record_response.code} msg = {list_record_response.msg}")
        return getattr(list_record_response.data, 'items', [])

    def find_with_params(self, table_id, predicate="", page_size=100, sort=""):
        list_record_request = ListAppTableRecordRequest.builder() \
            .page_size(page_size) \
            .table_id(table_id) \
            .filter(predicate) \
            .sort(sort) \
            .build()

        list_record_response = self.client.base.v1.app_table_record.list(list_record_request)
        print(f"find end! code = {list_record_response.code} msg = {list_record_response.msg}")
        return getattr(list_record_response.data, 'items', [])

    def update(self, table_id, records_need_update):
        """
        批量更新记录
        :param table_id:
        :param records_need_update: [{"record_id": record_id,"fields": item}]
        :return:
        """
        # 批量更新记录
        batch_update_records_request = BatchUpdateAppTableRecordRequest().builder() \
            .table_id(table_id) \
            .request_body(
            BatchUpdateAppTableRecordRequestBody.builder()
            .records(records_need_update)
            .build()
        ).build()
        response = self.client.base.v1.app_table_record.batch_update(batch_update_records_request)
        print(f'update end ! code:{response.code} {response.msg} size: {len(records_need_update)}')
        return response.success()

    def insert(self, table_id, records_need_insert):
        """
        批量插入记录
        :param table_id:
        :param records_need_insert: [{"fields": item}]
        :return:
        """
        batch_insert_records_request = BatchCreateAppTableRecordRequest().builder() \
            .table_id(table_id) \
            .request_body(
            BatchCreateAppTableRecordRequestBody.builder()
            .records(records_need_insert)
            .build()
        ).build()
        response = self.client.base.v1.app_table_record.batch_create(batch_insert_records_request)
        print(f'insert end ! code:{response.code} {response.msg} size:{len(records_need_insert)}')
        return response.success()

    def delete(self, table_id, records):
        batch_delete_records_request = BatchDeleteAppTableRecordRequest().builder() \
            .table_id(table_id) \
            .request_body(
            BatchDeleteAppTableRecordRequestBody.builder()
            .records(records)
            .build()
        ).build()
        batch_delete_records_response = self.client.base.v1.app_table_record.batch_delete(batch_delete_records_request)
        print(f'delete end! {batch_delete_records_response.code} {batch_delete_records_response.msg}')

    # 覆盖更新，适用条数较少的表格
    def insert_with_clear(self, table_id, records_need_insert):
        records = self.read(table_id)

        # 插入
        self.insert(table_id, [{'fields': record} for record in records_need_insert])

        # 清空表
        if records:
            self.delete(table_id, [record.record_id for record in records])

    # 合并更新，多余的插入
    def update_by_zip(self, table_id, records_need_insert):
        records = list(self.read(table_id))
        if records:
            want_update = records_need_insert[:len(records)]
            want_insert = records_need_insert[len(records):]

            # 更新
            updated = [{'record_id': cloud.record_id, 'fields': {**cloud.fields, **want}} for want, cloud in
                       zip(want_update, records)]

            if updated:
                self.update(table_id, updated)
        else:
            want_insert = records_need_insert
        # 插入
        if want_insert:
            self.insert(table_id, [{'fields': record} for record in want_insert])

    # 批量更新记录或插入记录
    def insert_or_update_all(self, table_id, data: Dict, filter_key, function):
        filter_value = map(lambda x: f"CurrentValue.[{filter_key}] = \"{x}\"", data.keys())
        list_filter = f"OR({','.join(filter_value)})"

        records = self.find(table_id, list_filter)

        # 根据filter_key把记录映射到map
        if records:
            record_map = {record.fields[filter_key]: record for record in records if record.fields}
        else:
            record_map = {}

        # 填充数据
        inserted = []
        updated = []

        for key, value in data.items():
            if key in record_map:
                item = function(key, value, record_map[key].fields)
                updated.append({"record_id": record_map[key].record_id,
                                "fields": item})
            else:
                item = function(key, value, {})
                inserted.append({"fields": item})

        # 批量追加记录
        if inserted:
            self.insert(table_id, inserted)

        # 批量更新记录
        if updated:
            self.update(table_id, updated)

    # 小批量更新记录或插入记录（最大size=100）
    def insert_or_update(self, table_id, data: List[Dict], filter_key, skip_update=False):
        filter_value = [f"CurrentValue.[{filter_key}] = \"{item[filter_key]}\"" for item in data]
        list_filter = f"OR({','.join(filter_value)})"

        records = self.find(table_id, list_filter)

        # 找到
        if records:
            print(f"find {len(records)} records")
            record_map = {record.fields[filter_key]: record for record in records if record.fields}
        else:
            print(f"find 0 records")
            record_map = {}

        # 填充数据
        inserted = []
        updated = []

        for item in data:
            if item[filter_key] in record_map:
                updated.append({"record_id": record_map[item[filter_key]].record_id, "fields": item})
            else:
                inserted.append({"fields": item})

        insert_result = True
        update_result = True

        # 批量追加记录
        if inserted:
            insert_result = self.insert(table_id, inserted)

        # 批量更新记录
        if updated and not skip_update:
            update_result = self.update(table_id, updated)

        return insert_result, update_result

    #  去重
    def distinct(self, table_id, filter_key):
        records = list(self.read(table_id))

        # 使用字典来跟踪已经见过的值
        seen = {}
        duplicates = []

        # 遍历记录，找出重复项
        for record in records:
            if record.fields and filter_key in record.fields:
                key_value = record.fields[filter_key]
                if key_value in seen:
                    duplicates.append(record.record_id)
                else:
                    seen[key_value] = record.record_id

        # 删除重复记录
        if duplicates:
            self.delete(table_id, duplicates)
            print(f"已删除 {len(duplicates)} 条重复记录")
        else:
            print("未发现重复记录")
