from datetime import datetime
import inspect
import os

class log():
    """ Prints statements to the console if they are sent with a log level contained within the global log class."""
    all_log_codes = [
        "Server",
        "Redis",
        "RDBMS",
        "Client",
        "Game",
        "Player",
        "Event",
        "Memory",
        "CurrentDev"
    ]

    csv_delimiter = "|"
    newline = "\n"

    csv_headers = csv_delimiter.join(["log_type", "log_code", "log_detail", "scenario", "context_id", "log_time", "log_message", "\n"])

    def __init__(self, log_codes=[], log_detail=10, log_file="log.txt", log_all=False, restart_log_file=True):
        self.log_file = log_file
        self.log_codes = log_codes
        self.log_detail = log_detail
        self.log_all = log_all
        self.log_history = []
        self.log_skipped = []

        if restart_log_file:
            with open(log_file, 'w'): pass

        for log_code in log_codes:
            if log_code not in log.all_log_codes:
                raise ValueError("log_code supplied invalid")

    def log(self, log_type, log_code, log_message, log_detail=1, scenario=None, context_id="", log_to_file=False, log_override=False):
        """ Main log function
            log_type            - the type of message (error, info, warning)
            log_code            - the category of the system that the log refers to (see log.all_log_codes)
            log_detail          - how granular the log entry is, lower values give a broader overview (1-10)
            scenario            - context information, normally the calling function
            log_message         - the message to be logged
            context_id          - Any relevant ids
            log_to_file         - whether the log message is written to file
            log_override        - to force logging even if the config is set lower
        """
        if log_code not in log.all_log_codes:
            raise ValueError("log_code supplied invalid")

        log_time = str(datetime.now())
        if scenario is None:
            scenario = self.caller_name()

        log_values = [log_type, log_code, log_detail, scenario, context_id, log_time, log_message, log.newline]
        log_values = [str(value) for value in log_values]

        console_log_string = ""
        for value in log_values:
            console_log_string += "[" + value + "]"

        console_log_string += log.newline
        csv_log_string = log.csv_delimiter.join(log_values) + log.newline

        if (log_code in self.log_codes and log_detail <= self.log_detail) or log_override or self.log_all:
            self.log_history.append(console_log_string)
            print(console_log_string)
            if log_to_file:
                with open(self.log_file, "a") as log_file:
                    if (os.fstat(log_file.fileno()).st_size == 0):  # add headers if empty file
                        log_file.write(log.csv_headers)

                    log_file.write(csv_log_string)
        else:
            self.log_skipped.append(csv_log_string)

    @classmethod
    def caller_name(cls, skip=2):
        """Get a name of a caller in the format module.class.method

           `skip` specifies how many levels of stack to skip while getting caller
           name. skip=1 means "who calls me", skip=2 "who calls my caller" etc.

           An empty string is returned if skipped levels exceed stack height

            Thanks: http://stackoverflow.com/a/9812105/2276412
        """
        stack = inspect.stack()
        start = 0 + skip
        if len(stack) < start + 1:
          return ''
        parentframe = stack[start][0]    

        name = []
        module = inspect.getmodule(parentframe)
        # `modname` can be None when frame is executed directly in console
        # TODO(techtonik): consider using __main__
        if module:
            name.append(module.__name__)
        # detect classname
        if 'self' in parentframe.f_locals:
            # I don't know any way to detect call from the object method
            # XXX: there seems to be no way to detect static method call - it will
            #      be just a function call
            name.append(parentframe.f_locals['self'].__class__.__name__)
        codename = parentframe.f_code.co_name
        if codename != '<module>':  # top level usually
            name.append( codename ) # function or a method
        del parentframe
        return ".".join(name)

# Configure this run
log_codes = [
    "Server",
    "Redis",
    "RDBMS",
    "Client",
    "Game",
    "Player",
    "Event",
    "CurrentDev"
]

log_handler = log(log_codes=log_codes, log_detail=3, log_file="2016-06-18Log.txt")