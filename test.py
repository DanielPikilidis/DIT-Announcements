from datetime import datetime
from time import mktime

now = datetime.now()

print(mktime(datetime.utcnow().timetuple()))