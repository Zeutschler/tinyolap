# import datetime
#
#
# class Errors:
#     """
#     Simple error message collector.
#     """
#     errors = []
#
#     @staticmethod
#     def clear():
#         if Errors.errors:
#             Errors.errors.clear()
#
#     @staticmethod
#     def add(message: str, innerexception: str = None):
#         Errors.errors.append({"timestamp": datetime.datetime.now(), "message": message, "innerexception": innerexception})
#
#     @staticmethod
#     def Last():
#         if len(Errors.errors):
#             return Errors.errors[-1]["message"]
#         return None
#
#     @staticmethod
#     def exists(self):
#         return len(Errors.errors) > 0
#
