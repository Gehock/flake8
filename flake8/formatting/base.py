"""The base class and interface for all formatting plugins."""
from __future__ import print_function


class BaseFormatter(object):
    """Class defining the formatter interface.

    .. attribute:: options

        The options parsed from both configuration files and the command-line.

    .. attribute:: filename

        If specified by the user, the path to store the results of the run.

    .. attribute:: output_fd

        Initialized when the :meth:`start` is called. This will be a file
        object opened for writing.

    .. attribute:: newline

        The string to add to the end of a line. This is only used when the
        output filename has been specified.
    """

    def __init__(self, options):
        """Initialize with the options parsed from config and cli.

        This also calls a hook, :meth:`after_init`, so subclasses do not need
        to call super to call this method.

        :param optparse.Values options:
            User specified configuration parsed from both configuration files
            and the command-line interface.
        """
        self.options = options
        self.filename = options.output_file
        self.output_fd = None
        self.newline = '\n'
        self.after_init()

    def after_init(self):
        """Initialize the formatter further."""
        pass

    def start(self):
        """Prepare the formatter to receive input.

        This defaults to initializing :attr:`output_fd` if :attr:`filename`
        """
        if self.filename:
            self.output_fd = open(self.filename, 'w')

    def handle(self, error):
        """Handle an error reported by Flake8.

        This defaults to calling :meth:`format`, :meth:`format_source`, and
        then :meth:`write`. To extend how errors are handled, override this
        method.

        :param error:
            This will be an instance of :class:`~flake8.style_guide.Error`.
        :type error:
            flake8.style_guide.Error
        """
        line = self.format(error)
        source = self.format_source(error)
        self.write(line, source)

    def format(self, error):
        """Format an error reported by Flake8.

        This method **must** be implemented by subclasses.

        :param error:
            This will be an instance of :class:`~flake8.style_guide.Error`.
        :type error:
            flake8.style_guide.Error
        :returns:
            The formatted error string.
        :rtype:
            str
        """
        raise NotImplementedError('Subclass of BaseFormatter did not implement'
                                  ' format.')

    def format_source(self, error):
        """Format the physical line generating the error.

        :param error:
            This will be an instance of :class:`~flake8.style_guide.Error`.
        :returns:
            The formatted error string if the user wants to show the source.
            If the user does not want to show the source, this will return
            ``None``.
        :rtype:
            str
        """
        if not self.options.show_source:
            return None
        pointer = (' ' * error.column_number) + '^'
        # Physical lines have a newline at the end, no need to add an extra
        # one
        return error.physical_line + pointer

    def write(self, line, source):
        """Write the line either to the output file or stdout.

        This handles deciding whether to write to a file or print to standard
        out for subclasses. Override this if you want behaviour that differs
        from the default.

        :param str line:
            The formatted string to print or write.
        """
        if self.output_fd is not None:
            write = self.output_fd.write
            output_func = lambda line: write(line + self.newline)
        else:
            output_func = print

        output_func(line)
        if source:
            output_func(source)

    def stop(self):
        """Clean up after reporting is finished."""
        if self.output_fd is not None:
            self.output_fd.close()
            self.output_fd = None
