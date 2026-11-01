using System.IO.Pipes;
using System.Text;
using System.Text.Json;

namespace Remi;

/// <summary>
/// Named-pipe IPC (the Windows analog of voisu's Unix-socket control channel).
/// One newline-terminated request per connection; one newline-terminated response back.
/// </summary>
public static class Ipc
{
    public const string PipeName = "remi";

    public static async Task ServeAsync(Func<string, string> handler, CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            NamedPipeServerStream? pipe = null;
            try
            {
                pipe = new NamedPipeServerStream(
                    PipeName, PipeDirection.InOut, 1, PipeTransmissionMode.Byte, PipeOptions.Asynchronous);
                await pipe.WaitForConnectionAsync(ct).ConfigureAwait(false);

                string? line;
                using (var reader = new StreamReader(pipe, new UTF8Encoding(false), false, 1024, leaveOpen: true))
                {
                    line = await reader.ReadLineAsync(ct).ConfigureAwait(false);
                }

                string response;
                try { response = handler(line ?? ""); }
                catch (Exception ex) { response = JsonSerializer.Serialize(new { error = ex.Message }); }

                var bytes = Encoding.UTF8.GetBytes(response + "\n");
                await pipe.WriteAsync(bytes, ct).ConfigureAwait(false);
                await pipe.FlushAsync(ct).ConfigureAwait(false);
            }
            catch (OperationCanceledException) { break; }
            catch (IOException) { /* client dropped mid-request — keep serving */ }
            catch (ObjectDisposedException) { /* shutting down */ }
            finally
            {
                try { if (pipe is { IsConnected: true }) pipe.Disconnect(); } catch { }
                pipe?.Dispose();
            }
        }
    }

    public static string? Send(string command)
    {
        try
        {
            using var pipe = new NamedPipeClientStream(".", PipeName, PipeDirection.InOut);
            pipe.Connect(2000);
            var req = Encoding.UTF8.GetBytes(command + "\n");
            pipe.Write(req, 0, req.Length);
            pipe.Flush();
            using var reader = new StreamReader(pipe, new UTF8Encoding(false), false, 1024, leaveOpen: true);
            return reader.ReadLine();
        }
        catch
        {
            return null;
        }
    }
}
