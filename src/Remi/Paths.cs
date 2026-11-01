namespace Remi;

public static class Paths
{
    public static readonly string AppDataRoaming = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "remi");

    public static readonly string AppDataLocal = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "remi");

    public static string ConfigFile => Path.Combine(AppDataRoaming, "config.toml");
    public static string HistoryFile => Path.Combine(AppDataLocal, "history.jsonl");
    public static string ModelsDir => Path.Combine(AppDataLocal, "models");
    public static string CrashLogFile => Path.Combine(AppDataLocal, "crash.log");

    /// <summary>Sibling app's models — remi borrows voice-trans models instead of re-downloading them.</summary>
    public static string VoiceTransModelsDir => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "voice-trans", "models");

    static Paths()
    {
        Directory.CreateDirectory(AppDataRoaming);
        Directory.CreateDirectory(ModelsDir);
    }
}
