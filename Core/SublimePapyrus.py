import sublime, sublime_plugin, re, os, sys
# ST2 uses Python 2.6 and ST3 uses Python 3.3.
PYTHON_VERSION = sys.version_info
if PYTHON_VERSION[0] == 2:
    import ConfigParser
    from StringIO import StringIO
    import imp
    buildPackage = os.path.join(os.path.split(os.getcwd())[0], "Default", "exec.py")
    imp.load_source("BUILD_SYSTEM", buildPackage)
    del buildPackage
    import BUILD_SYSTEM
    USER_SETTINGS = sublime.load_settings('SublimePapyrus.sublime-settings')
elif PYTHON_VERSION[0] == 3:
    import configparser
    from io import StringIO
    import importlib
    BUILD_SYSTEM = importlib.import_module("Default.exec")

# INI related variables.
DEFAULT_INI_LOCATION = os.path.expanduser("~\\Documents\\SublimePapyrus.ini")
INI_LOCATION = DEFAULT_INI_LOCATION
if (os.path.exists("C:\\Program Files (x86)")):
    END_USER_ROOT = "C:\\Program Files (x86)\\Steam\\steamapps\\common\\skyrim"
else:
    END_USER_ROOT = "C:\\Program Files\\Steam\\steamapps\\common\\skyrim"
END_USER_OUTPUT   = os.path.join(END_USER_ROOT, "Data\\Scripts")
END_USER_SCRIPTS  = os.path.join(END_USER_OUTPUT, "Source")
END_USER_COMPILER = os.path.join(END_USER_ROOT, "Papyrus Compiler\\PapyrusCompiler.exe")
END_USER_FLAGS    = "TESV_Papyrus_Flags.flg"
DEFAULT_INI_TEXT = """[Skyrim]
# The path to the folder containing the vanilla Skyrim .psc files.
scripts=%s

# The path to PapyrusCompiler.exe
compiler=%s

# The folder you wish to output the .pex files to. If commented out (# at the start of a line), then .pex files are placed in the folder one level above the .psc file.
output=%s

# The name of the file containing Papyrus' flags. The file has to be among the folders that are imported, which includes the scripts folder defined above and the folder containing the .psc file(s) to be compiled.
flags=%s

[Import]
# Additional folders that contain .psc you wish to import when compiling.
# Template:
# pathN=Drive:\\Folder1\\Folder2\\Folder_with_PSC_files
# The order in which .psc files are processed is:
# - the path containing the .psc file to compile provided that this path is not the same as the path containing the vanilla Skyrim .psc files
# - path1
# - path2
# .
# .
# .
# - pathN
# - the path containing the vanilla Skyrim .psc files ("scripts=" key above)
#
# For example if you want to separate the vanilla scripts (defined in the "scripts=" key) and SKSE scripts into their own folders (defined as an additional import), then you would define the path to SKSE's .psc files as the value for a "pathN" key.
# path1=Drive:\\Folder\\Subfolder_containing_SKSE_PSC_files
#

[Debug]
# For advanced users only! You can add arguments like \"keepasm\", \"quiet\", etc. to options here. Below is an example:
#
# arg0=debug
# arg1=keepasm
# .
# .
# .
# argN=optimize
#
# You should only use these arguments if you know what you are doing! Run the Papyrus compiler with the argument \"/?\" to get a full list of valid arguments.
""" % (END_USER_SCRIPTS, END_USER_COMPILER, END_USER_OUTPUT, END_USER_FLAGS)

# Variables specific to compiler error highlighting.
ERROR_HIGHLIGHT_KEY = "papyrus_error"
ERROR_HIGHLIGHT_SCOPE = "invalid"
PAPYRUS_SCRIPT_EXTENSION = ".psc"

# ST3's API is ready to be used.
def plugin_loaded():
    global USER_SETTINGS
    USER_SETTINGS = sublime.load_settings('SublimePapyrus.sublime-settings')
    updateINIPath()

# Reads the path, which may have been defined by the user, to the INI file containing settings specific to the Papyrus build system.
def updateINIPath():
    global INI_LOCATION
    iniPath = USER_SETTINGS.get('ini_path', "")
    if iniPath == "":
        if INI_LOCATION != DEFAULT_INI_LOCATION:
            INI_LOCATION = DEFAULT_INI_LOCATION
    elif iniPath != INI_LOCATION:
        if iniPath.endswith(".ini"):
            folderPath = os.path.dirname(iniPath)
            if os.path.exists(folderPath) == False:
                os.mkdir(folderPath)
        else:
            if os.path.exists(iniPath) == False:
                os.mkdir(iniPath)
            iniPath += "\\SublimePapyrus.ini"
        INI_LOCATION = iniPath

# Returns Papyrus compiler arguments based on the user's settings in the INI file.
def getPrefs(filePath):
    fileDir, fileName = os.path.split(filePath)
    ret = {}
    ret["compiler"] = END_USER_COMPILER
    ret["output"] = END_USER_OUTPUT
    ret["flags"] = END_USER_FLAGS
    ret["import"] = END_USER_SCRIPTS
    updateINIPath()
    if (os.path.exists(INI_LOCATION)):
        if PYTHON_VERSION[0] == 2:
            parser = ConfigParser.ConfigParser()
        elif PYTHON_VERSION[0] == 3:
            parser = configparser.ConfigParser()
        parser.read([INI_LOCATION])
        if (parser.has_section("Skyrim")):
            if(parser.has_option("Skyrim", "compiler")):
                ret["compiler"] = parser.get("Skyrim", "compiler")
            if(parser.has_option("Skyrim", "output")):
                ret["output"] = parser.get("Skyrim", "output")
            else:
                ret["output"] = os.path.dirname(fileDir)
            if(parser.has_option("Skyrim", "flags")):
                ret["flags"] = parser.get("Skyrim", "flags")
        ret["import"] = []
        if (fileDir != parser.get("Skyrim", "scripts")):
            ret["import"].append(fileDir)
        if (parser.has_section("Import")):
            for configKey, configValue in parser.items("Import"):
                if (configKey.startswith("path")):
                    if (os.path.exists(configValue)):
                        ret["import"].append(configValue)
        if (parser.get("Skyrim", "scripts") not in ret["import"]):
            ret["import"].append(parser.get("Skyrim", "scripts"))
        ret["debug"] = []
        if (parser.has_section("Debug")):
            for configKey, configValue in parser.items("Debug"):
                if (configKey.startswith("arg")):
                    ret["debug"].append(configValue)
        if PYTHON_VERSION[0] == 2:
            ret["import"] = ";".join(filter(None, ret["import"]))
        elif PYTHON_VERSION[0] == 3:
            ret["import"] = ";".join([_f for _f in ret["import"] if _f])
    else:
        sublime.status_message("Could not find a configuration file. Falling back to default values.")
        ret["debug"] = []
    ret["filename"] = fileName
    if os.path.exists(ret["compiler"]) == False:
        sublime.status_message("Compiler does not exist at the given path (\"%s\")." %(ret["compiler"]))
        return None
    return ret

# Generates an INI file based on the template defined in the variable DEFAULT_INI_TEXT.
class CreateDefaultSettingsFileCommand(sublime_plugin.WindowCommand):
    def run(self, **args):
        updateINIPath()
        if os.path.isfile(INI_LOCATION):
            if sublime.ok_cancel_dialog("INI file already exists at %s.\n Do you want to open the file?" % INI_LOCATION):
                self.window.open_file(INI_LOCATION)
        else:
            outHandle = open(INI_LOCATION, "w")
            outHandle.write(DEFAULT_INI_TEXT)
            outHandle.close()
            self.window.open_file(INI_LOCATION)

# Runs the Papyrus compiler with properly formatted arguments based on settings in the INI file.
class CompilePapyrusCommand(sublime_plugin.WindowCommand):
    def run(self, **args):
        config = getPrefs(args["cmd"])
        if config != None:
            if (len(config) > 0):
                args["cmd"] = [config["compiler"], config["filename"]]
                args["cmd"].append("-f=%s" % config["flags"])
                args["cmd"].append("-i=%s" % config["import"])
                args["cmd"].append("-o=%s" % config["output"])
                for debugarg in config["debug"]:
                    if debugarg.startswith("-"):
                        args["cmd"].append("%s" % debugarg)
                    else:
                        args["cmd"].append("-%s" % debugarg)
                args["working_dir"] = os.path.dirname(config["compiler"])
                self.window.run_command("exec", args)
            else:
                sublime.status_message("No configuration for %s" % os.path.dirname(args["cmd"]))

# Disassembles bytecode (.pex) to assembly (.pas)
class DisassemblePapyrusCommand(sublime_plugin.WindowCommand):
    def run(self, **args):
        scriptPath = args["cmd"]
        scriptDir = os.path.dirname(scriptPath)
        assembler = os.path.join(scriptDir, "PapyrusAssembler.exe")            
        scriptPath = os.path.splitext(os.path.basename(scriptPath))[0]
        args["cmd"] = [assembler, scriptPath]
        args["cmd"].append("-V")
        args["cmd"].append("-D")
        args["working_dir"] = scriptDir
        self.window.run_command("exec", args)
        disassembly = os.path.join(scriptDir, scriptPath + ".disassemble.pas")
        disassemblyFinal = os.path.join(scriptDir, scriptPath + ".pas")
        os.rename(disassembly, disassemblyFinal)
        if (os.path.exists(disassemblyFinal)):
            self.window.open_file(disassemblyFinal)

# Generates bytecode (.pex) from assembly (.pas).
class AssemblePapyrusCommand(sublime_plugin.WindowCommand):
    def run(self, **args):
        scriptPath = args["cmd"]
        scriptDir = os.path.dirname(scriptPath)
        assembler = os.path.join(scriptDir, "PapyrusAssembler.exe")            
        scriptPath = os.path.splitext(os.path.basename(scriptPath))[0]
        args["cmd"] = [assembler, scriptPath]
        args["cmd"].append("-V")
        args["working_dir"] = scriptDir
        self.window.run_command("exec", args)

# Looks for matching files in all input paths defined in the INI file based on the given regular expression.
def GetMatchingFiles(self, filename):
    if filename != "":
        folderpaths = []
        filepath = self.window.active_view().file_name()
        if filepath != None and filepath != "":
            folderpath = os.path.split(filepath)[0]
            if os.path.exists(folderpath):
                folderpaths.append(folderpath)
        if PYTHON_VERSION[0] == 2:
            parser = ConfigParser.ConfigParser()
        elif PYTHON_VERSION[0] == 3:
            parser = configparser.ConfigParser()
        updateINIPath()
        parser.read([INI_LOCATION])
        if parser.has_section("Import"):
            for configKey, configValue in parser.items("Import"):
                if configKey.startswith("path"):
                    if os.path.exists(configValue):
                        folderpaths.append(configValue)
        if parser.has_section("Skyrim"):
            if parser.has_option("Skyrim", "scripts"):
                folderpath = parser.get("Skyrim", "scripts")
                if folderpath not in folderpaths:
                    if os.path.exists(folderpath):
                        folderpaths.append(folderpath)
        matches = []
        searchterm = filename.lower()
        if searchterm.startswith("^"):
            searchterm = searchterm[1:]
        if searchterm.endswith("$"):
            searchterm = searchterm[:-1]
        if searchterm.endswith(PAPYRUS_SCRIPT_EXTENSION):
            searchterm = searchterm[:-4]
        pattern = "^(" + searchterm + "\\" + PAPYRUS_SCRIPT_EXTENSION + ")$"
        regex = re.compile(pattern, re.IGNORECASE)
        for folderpath in folderpaths:
            if not folderpath.endswith("\\"):
                folderpath += "\\"
            for filename in os.listdir(folderpath):
                match = regex.findall(filename)
                if len(match) > 0:
                    filepath = folderpath + filename
                    if filepath not in matches:
                        matches.append(filepath)
        nummatches = len(matches)
        if nummatches == 0:
            sublime.status_message("Could not find script matching the regular expression \"%s\"" % pattern)
        elif nummatches == 1:
            self.window.open_file(matches[0])
        elif nummatches > 1:
            self.window.run_command("open_papyrus_script_selection", {"items": matches})

# Scans the current buffer for a script header that declares a parent script and then tries to open the parent script.
class OpenPapyrusParentScriptCommand(sublime_plugin.WindowCommand):
    def run(self):
        source = self.window.active_view().file_name()
        if source != None and os.path.exists(source):
            with open(source) as f:
                pattern = "^\s*scriptname\s+\S+\s+extends\s+(\S+).*$"
                regex = re.compile(pattern, re.IGNORECASE)
                for line in f:
                    match = regex.findall(line)
                    if len(match) > 0:
                        GetMatchingFiles(self, match[0])
                        return
            sublime.status_message("Parent script not declared in \"%s\"" % source)

# Tries to open the file(s) matching a given regular expression. 
class OpenPapyrusScriptCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.show_input_panel("Open script:", "", self.on_done, None, None)

    def on_done(self, text):
        if text == "":
            view = self.window.active_view()
            if view != None:
                for region in view.sel():
                    text = view.substr(region)
                    break
            else:
                return
        if text != "":
            GetMatchingFiles(self, text)
        else:
            sublime.status_message("No input")

# Shows a menu with a list of scripts that match the regular expression passed on to GetMatchingFiles.
class OpenPapyrusScriptSelectionCommand(sublime_plugin.WindowCommand):
    def run(self, **args):
        items = args["items"]
        if items != None and len(items) > 0:
            self.items = items
            if PYTHON_VERSION[0] == 2:
                self.window.show_quick_panel(items, self.on_select, 0)
            elif PYTHON_VERSION[0] == 3:
                self.window.show_quick_panel(items, self.on_select, 0, -1, None)

    def on_select(self, index):
        if index >= 0:
            self.window.open_file(self.items[index])

# Base class that is used in the framework for showing a list of valid arguments and then inserting them.
# Libraries that need this functionality should import at least "sublime", "sublime_plugin", "sys", and this module.
# ST2 requires using the "imp" module to load this module first via the "load_source" function. ST3 can simply use "from SublimePapyrus import SublimePapyrus".
# Classes implementing this functionality need to inherit the "PapyrusShowSuggestionsCommand" class and override the "get_items" method.
# "get_items" should return a dictionary where the keys are the descriptions shown to the user and the values are what is inserted into the buffer.
class PapyrusShowSuggestionsCommand(sublime_plugin.TextCommand):
    def run(self, edit, **args):
        selections = self.view.sel()
        if selections != None and len(selections) == 1:
            region = selections[0]
            self.argument = region
        items = self.get_items()
        if items != None:
            sortedKeysAndValues = sorted(zip(list(items.keys()), list(items.values())))
            sortedKeys = [key for (key, value) in sortedKeysAndValues]
            sortedValues = [value for (key, value) in sortedKeysAndValues]
            self.items = sortedKeys
            self.values = sortedValues
            if PYTHON_VERSION[0] == 2:
                self.view.window().show_quick_panel(self.items, self.on_select, 0)
            elif PYTHON_VERSION[0] == 3:
                self.view.window().show_quick_panel(self.items, self.on_select, 0, -1, None)

    def get_items(self, **args):
        return None

    def on_select(self, index):
        if index >= 0:
            value = str(self.values[index])
            if value.isdigit() or value != "":
                args = {"region_start": self.argument.a, "region_end": self.argument.b, "replacement": value}
            else:
                args = {"region_start": self.argument.a, "region_end": self.argument.b, "replacement": str(self.items[index])}
            self.view.run_command("papyrus_insert_suggestion", args)

# Inserts the value chosen in the class that inherits "PapyrusShowSuggestionsCommand".
class PapyrusInsertSuggestionCommand(sublime_plugin.TextCommand):
    def run(self, edit, **args):
        region = sublime.Region(args["region_start"], args["region_end"])
        self.view.erase(edit, region)
        if args["replacement"].isdigit():
            self.view.insert(edit, args["region_start"], args["replacement"])
        else:
            self.view.insert(edit, args["region_start"], "\"" + args["replacement"] + "\"")

# Manually clear any sections that were highlighted as a result of a failed compilation.
class ClearPapyrusCompilerErrorHighlightsCommand(sublime_plugin.WindowCommand):
    def run(self, **args):
        source = sublime.active_window().active_view()
        if source != None:
            source.erase_regions(ERROR_HIGHLIGHT_KEY)

# Checks the build result for errors and, depending on the settings, highlights lines that caused errors and/or hides the build results when there are no errors.
class ExecCommand(BUILD_SYSTEM.ExecCommand):
    def finish(self, proc):
        super(ExecCommand, self).finish(proc)
        source = sublime.active_window().active_view()
        if source != None:
            if source.file_name().endswith(PAPYRUS_SCRIPT_EXTENSION):
                source.erase_regions(ERROR_HIGHLIGHT_KEY)
                if USER_SETTINGS.get('highlight_compiler_errors', False):
                    output = self.output_view.substr(sublime.Region(0, self.output_view.size()))
                    if output != None:
                        pattern = self.output_view.settings().get("result_file_regex")
                        if pattern != None:
                            errors = self.GetErrors(output, pattern)
                            if errors != None:
                                regions = self.GetRegions(source, errors)
                                if regions != None:
                                    source.add_regions(ERROR_HIGHLIGHT_KEY, regions, ERROR_HIGHLIGHT_SCOPE)
                            elif USER_SETTINGS.get('hide_successful_build_results', False):
                                self.window.run_command("hide_panel", {"panel": "output.exec"})

    def GetErrors(self, output, pattern):
        lines = output.rstrip().split('\n')
        matches = []
        regex = re.compile(pattern)
        for line in lines:
            match = regex.findall(line)
            if len(match) > 0:
                matches.append(match)
        if len(matches) > 0:
            return matches
        else:
            return None

    def GetRegions(self, view, errors):
        regions  = []
        for error in errors:
            region = view.line(sublime.Region(view.text_point(int(error[0][1]) - 1, 0)))
            regions.append(region)
            del region
        if len(regions) > 0:
            return regions
        else:
            return None