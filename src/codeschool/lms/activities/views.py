import model_reference


def main_activity_list(request):
    page = model_reference.load('main-activity-list')
    return page.serve(request)