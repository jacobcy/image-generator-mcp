import json

# 用于模拟 API 响应的辅助类
class MockResponse:
    def __init__(self, json_data, status_code, content=b'dummy_img_bytes'):
        self._json_data = json_data
        self.status_code = status_code
        self.content = content
        self.text = json.dumps(json_data) if json_data is not None else ""

    def json(self):
        if self._json_data is None:
            raise json.JSONDecodeError("No JSON object could be decoded", "", 0)
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            # Using a simple Exception for mock purposes
            raise Exception(f"Mock HTTP Error {self.status_code}")

    def iter_content(self, chunk_size=8192):
        # Simulate yielding byte chunks
        yield self.content

# --- 模拟成功的 API 响应 --- #

# /imagine 调用成功，返回 job_id
mock_imagine_success = MockResponse(
    {"status": "SUCCESS", "data": {"jobId": "mock_job_123"}},
    200
)

# /fetch 调用成功，返回包含 cdnImage 的数据 (同步模式)
mock_fetch_success_sync = MockResponse(
    {
        "status": "SUCCESS",
        "data": {
            "cdnImage": "http://mock.url/image_sync.png",
            "progress": "100",
            "components": ["upsample1", "upsample2", "variation1", "variation2"],
            "seed": "12345"
        }
    },
    200
)

# /fetch 调用仍在进行中 (用于轮询测试)
mock_fetch_pending = MockResponse(
    {
        "status": "PENDING",
        "data": {
            "progress": "50"
        }
    },
    200
)

# /fetch 调用失败
mock_fetch_failure = MockResponse(
    {
        "status": "FAILURE",
        "error": "Image generation failed"
    },
    200 # API might return 200 even on logical failure
)

# 图像下载 (requests.get) 成功
mock_download_success = MockResponse(None, 200, content=b'mock image data')

# 图像下载 (requests.get) 失败
mock_download_failure = MockResponse(None, 404)

# --- 模拟失败的 API 响应 --- #

# /imagine 调用失败 (例如，API密钥无效)
mock_imagine_failure_auth = MockResponse(
    {"status": "FAILURE", "error": "Invalid API Key"},
    401
)

# /imagine 调用失败 (服务器错误)
mock_imagine_failure_server = MockResponse(
    {"status": "FAILURE", "error": "Internal Server Error"},
    500
)

# /fetch 调用失败 (找不到 Job ID)
mock_fetch_failure_not_found = MockResponse(
    {"status": "FAILURE", "error": "Job not found"},
    404
) 