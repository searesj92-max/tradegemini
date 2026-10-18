using System;
using System.Diagnostics;
using System.IO;
using System.Net.Sockets;
using System.Threading;
using System.Windows.Forms;

namespace Botrade
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            try
            {
                string projectDir = @"c:\Users\seares\Desktop\botrade";
                string pythonExe = @"C:\Users\seares\miniconda3\python.exe";

                if (File.Exists(pythonExe))
                {
                    // 1. Check and launch Options Desk Daemon (Port 8766)
                    if (!IsPortOpen("127.0.0.1", 8766))
                    {
                        ProcessStartInfo optPsi = new ProcessStartInfo
                        {
                            FileName = pythonExe,
                            Arguments = Path.Combine(projectDir, @"scripts\options_desk.py"),
                            WorkingDirectory = projectDir,
                            WindowStyle = ProcessWindowStyle.Hidden,
                            CreateNoWindow = true,
                            UseShellExecute = false
                        };
                        Process.Start(optPsi);
                    }

                    // 2. Check and launch Dashboard Server (Port 8765)
                    if (!IsPortOpen("127.0.0.1", 8765))
                    {
                        ProcessStartInfo dashPsi = new ProcessStartInfo
                        {
                            FileName = pythonExe,
                            Arguments = Path.Combine(projectDir, @"scripts\dashboard_server.py"),
                            WorkingDirectory = projectDir,
                            WindowStyle = ProcessWindowStyle.Hidden,
                            CreateNoWindow = true,
                            UseShellExecute = false
                        };
                        Process.Start(dashPsi);
                    }

                    // Wait up to 5 seconds for Dashboard Server port 8765
                    for (int i = 0; i < 25; i++)
                    {
                        Thread.Sleep(200);
                        if (IsPortOpen("127.0.0.1", 8765))
                            break;
                    }
                }

                // 3. Launch in dedicated Native Windows Desktop App window
                string edgePath = @"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe";
                string appUrl = "http://localhost:8765/options";

                if (File.Exists(edgePath))
                {
                    ProcessStartInfo edgePsi = new ProcessStartInfo
                    {
                        FileName = edgePath,
                        Arguments = "--app=" + appUrl,
                        WindowStyle = ProcessWindowStyle.Normal,
                        UseShellExecute = true
                    };
                    Process.Start(edgePsi);
                }
                else
                {
                    Process.Start(new ProcessStartInfo(appUrl) { UseShellExecute = true });
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show("Erro ao iniciar Botrade Desktop: " + ex.Message, "Botrade Desktop", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        static bool IsPortOpen(string host, int port)
        {
            try
            {
                using (var client = new TcpClient())
                {
                    var result = client.BeginConnect(host, port, null, null);
                    var success = result.AsyncWaitHandle.WaitOne(300);
                    if (!success) return false;
                    client.EndConnect(result);
                    return true;
                }
            }
            catch
            {
                return false;
            }
        }
    }
}
