using System.Security.Cryptography;
using System.Text;

namespace VoiceTrans;

/// <summary>Provider API keys, DPAPI-encrypted per Windows user (analog of voisu's secret-tool storage).</summary>
public static class KeyStore
{
    static byte[] Entropy(string provider) => Encoding.UTF8.GetBytes("voice-trans:" + provider);

    public static string PathFor(string provider) => Path.Combine(Paths.AppDataRoaming, provider + ".key");

    public static void Set(string provider, string secret)
    {
        var blob = ProtectedData.Protect(Encoding.UTF8.GetBytes(secret), Entropy(provider), DataProtectionScope.CurrentUser);
        File.WriteAllBytes(PathFor(provider), blob);
    }

    public static string? Get(string provider)
    {
        try
        {
            var p = PathFor(provider);
            if (!File.Exists(p)) return null;
            return Encoding.UTF8.GetString(ProtectedData.Unprotect(File.ReadAllBytes(p), Entropy(provider), DataProtectionScope.CurrentUser));
        }
        catch
        {
            return null;
        }
    }

    public static void Clear(string provider)
    {
        try { File.Delete(PathFor(provider)); } catch { /* nothing to clear */ }
    }
}
