from mr.developer.common import logger, do_checkout
from optparse import OptionParser
import logging
import os
import re
import sys


class Command(object):
    def __init__(self, develop):
        self.develop = develop


class CmdCheckout(Command):
    def __init__(self, develop):
        super(CmdCheckout, self).__init__(develop)
        self.parser=OptionParser(
            usage="%prog <options> [<package-regexps>]",
            description="Make a checkout of the packages matching the regular expressions.",
            add_help_option=False)

    def __call__(self):
        options, args = self.parser.parse_args(sys.argv[2:])

        regexp = re.compile("|".join("(%s)" % x for x in args))
        packages = {}
        for name in sorted(self.develop.sources):
            if not regexp.search(name):
                continue
            kind, url = self.develop.sources[name]
            packages.setdefault(kind, {})[name] = url
        if len(packages) == 0:
            if len(args) > 1:
                regexps = "%s or '%s'" % (", ".join("'%s'" % x for x in args[:-1]), args[-1])
            else:
                regexps = "'%s'" % args[0]
            logger.error("No package matched %s." % regexps)
            sys.exit(1)

        try:
            do_checkout(packages, self.sources_dir)
            logger.warn("Don't forget to run buildout again, so the checked out packages are used as develop eggs.")
        except ValueError, e:
            logger.error(e)
            sys.exit(1)

class CmdHelp(Command):
    def __init__(self, develop):
        super(CmdHelp, self).__init__(develop)
        self.parser = OptionParser(
            usage="%prog help [<command>]",
            description="Show help on the given command or about the whole script if none given.",
            add_help_option=False)

    def __call__(self):
        develop = self.develop
        if len(sys.argv) != 3 or sys.argv[2] not in develop.commands:
            print("usage: %s <command> [options] [args]" % os.path.basename(sys.argv[0]))
            print("\nType '%s help <command>' for help on a specific command." % os.path.basename(sys.argv[0]))
            print("\nAvailable commands:")
            f_to_name = {}
            for name, f in develop.commands.iteritems():
                f_to_name.setdefault(f, []).append(name)
            for cmd in sorted(x for x in dir(develop) if x.startswith('cmd_')):
                name = cmd[4:]
                f = getattr(develop, cmd)
                aliases = [x for x in f_to_name[f] if x != name]
                if len(aliases):
                    print("    %s (%s)" % (name, ", ".join(aliases)))
                else:
                    print("    %s" % name)
        else:
            print develop.commands[sys.argv[2]].parser.format_help()


class CmdList(Command):
    def __init__(self, develop):
        super(CmdList, self).__init__(develop)
        self.parser = OptionParser(
            usage="%prog list [<package-regexps>]",
            description="List the available packages, filtered if <package-regexps> is given.",
            add_help_option=False)
        self.parser.add_option("-a", "--auto-checkout", dest="auto_checkout",
                               action="store_true", default=False,
                               help="""Only show packages in auto-checkout list.""")
        self.parser.add_option("-l", "--long", dest="long",
                               action="store_true", default=False,
                               help="""Show URL and kind of package.""")
        self.parser.add_option("-s", "--status", dest="status",
                               action="store_true", default=False,
                               help="""Show checkout status.
                                       The first column in the output shows the checkout status:
                                       ' ' available for checkout
                                       'A' in auto-checkout list and checked out
                                       'C' not in auto-checkout list, but checked out
                                       '!' in auto-checkout list, but not checked out""")

    def __call__(self):
        options, args = self.parser.parse_args(sys.argv[2:])

        regexp = re.compile("|".join("(%s)" % x for x in args))
        sources = self.develop.sources
        sources_dir = self.develop.sources_dir
        auto_checkout = self.develop.auto_checkout
        for name in sorted(sources):
            if args:
                if not regexp.search(name):
                    continue
            if options.auto_checkout and name not in auto_checkout:
                continue
            kind, url = sources[name]
            if options.status:
                if os.path.exists(os.path.join(sources_dir, name)):
                    if name in auto_checkout:
                        print "A",
                    else:
                        print "C",
                else:
                    if name in auto_checkout:
                        print "!",
                    else:
                        print " ",
            if options.long:
                print "(%s)" % kind, name, url
            else:
                print name


class Develop(object):
    def __call__(self, sources, sources_dir, auto_checkout):
        self.sources = sources
        self.sources_dir = sources_dir
        self.auto_checkout = set(auto_checkout)

        logger.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(ch)

        self.cmd_checkout = CmdCheckout(self)
        self.cmd_help = CmdHelp(self)
        self.cmd_list = CmdList(self)

        self.commands = dict(
            help=self.cmd_help,
            checkout=self.cmd_checkout,
            co=self.cmd_checkout,
            list=self.cmd_list,
            ls=self.cmd_list,
        )

        if len(sys.argv) < 2:
            logger.info("Type '%s help' for usage." % os.path.basename(sys.argv[0]))
        else:
            self.commands.get(sys.argv[1], self.unknown)()

    def unknown(self):
        logger.error("Unknown command '%s'." % sys.argv[1])
        logger.info("Type '%s help' for usage." % os.path.basename(sys.argv[0]))
        sys.exit(1)

develop = Develop()