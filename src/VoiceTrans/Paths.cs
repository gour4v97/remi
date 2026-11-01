namespace VoiceTrans;

/// <summary>All on-disk locations used by voice-trans.</summary>
public static class Paths
{
    public static readonly string AppDataRoaming = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "voice-trans");

    public static readonly string AppDataLocal = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "voice-trans");

    public static string ConfigFile => Path.Combine(AppDataRoaming, "config.toml");
    public static string DictionaryFile => Path.Combine(AppDataRoaming, "dictionary.txt");
    public static string HistoryFile => Path.Combine(AppDataLocal, "history.jsonl");
    public static string ModelsDir => Path.Combine(AppDataLocal, "models");

    static Paths()
    {
        Directory.CreateDirectory(AppDataRoaming);
        Directory.CreateDirectory(ModelsDir);
    }
}
