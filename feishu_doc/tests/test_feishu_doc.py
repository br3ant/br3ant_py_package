import unittest
from feishu_doc import FeishuDocClient, FeishuToken
import itertools

feishu_client = FeishuDocClient(FeishuToken("MJaObCMH5atdJ2sdjkacTTUwn7g",
                                            "pt-rpJ6H2vGPT7q7xAMrpA3nXapeRJfP3J3YQ4r2meVAQAAAUADLhwAD2B5DTms"))
table_id = "tbluhEtMLbUPlGLF"


class TestFeushuDoc(unittest.TestCase):

    def test_insert_or_update(self):
        result = feishu_client.insert_or_update(table_id, [{"id": "111", "error_info": "error_1"},
                                                           {"id": "222", "error_info": "error_2"}], "id")
        self.assertEqual(result, (True, True))

    def test_insert(self):
        result = feishu_client.insert(table_id, [{"fields": {"id": "abc", "error_info": "error_1"}}])
        self.assertEqual(result, True)

    def test_distinct(self):
        feishu_client.distinct(table_id, 'id')
