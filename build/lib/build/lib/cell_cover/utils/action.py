def get_available_actions(image_id=None, job_id=None, filename=None):
    return ["upsample1", "upsample2", "variation1", "variation2"]

def execute_action(action, image_id=None, job_id=None, filename=None, api_key=None):
    return "/path/to/new/image.png"

def list_available_actions():
    return {"upsample1": "Upscale 1", "upsample2": "Upscale 2"}
