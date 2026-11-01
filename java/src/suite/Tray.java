package suite;

import java.awt.Color;
import java.awt.Font;
import java.awt.Graphics2D;
import java.awt.PopupMenu;
import java.awt.MenuItem;
import java.awt.SystemTray;
import java.awt.TrayIcon;
import java.awt.image.BufferedImage;

/** AWT SystemTray icon with state colors and menu (shared by both Java apps). */
public final class Tray {
    public static final Color VIOLET = new Color(0x7C, 0x5C, 0xD9);
    public static final Color RED = new Color(0xE5, 0x48, 0x4D);
    public static final Color AMBER = new Color(0xF5, 0xA6, 0x23);

    private Tray() {}

    /** Simpler direct construction — caller adds menu items then shows. */
    public static Holder create(String app, String letter, Color idleColor, String tooltip) {
        Holder h = new Holder();
        h.app = app;
        h.letter = letter;
        h.idleColor = idleColor;
        h.tooltip = tooltip;
        return h;
    }

    public static final class Holder {
        String app, letter, tooltip;
        Color idleColor;
        PopupMenu menu = new PopupMenu();
        TrayIcon icon;
        Color current = null;

        public void add(String label, Runnable action) {
            MenuItem item = new MenuItem(label);
            if (action != null) item.addActionListener(e -> new Thread(action, "tray-action").start());
            menu.add(item);
        }

        public void addSeparator() {
            menu.addSeparator();
        }

        public void setState(String state, String note) {
            Color c = switch (state) {
                case "recording" -> RED;
                case "thinking" -> AMBER;
                default -> idleColor;
            };
            if (icon != null) {
                icon.setImage(iconImage(c, letter));
                icon.setToolTip(app + " (Java) — " + note);
            } else {
                current = c;
            }
        }

        public void display() throws Exception {
            if (!SystemTray.isSupported()) throw new IllegalStateException("SystemTray not supported");
            icon = new TrayIcon(iconImage(idleColor, letter), app + " (Java) — " + tooltip);
            icon.setImageAutoSize(true);
            icon.setPopupMenu(menu);
            SystemTray.getSystemTray().add(icon);
        }

        public void notify(String title, String msg, boolean error) {
            if (icon != null) icon.displayMessage(title, msg,
                    error ? TrayIcon.MessageType.ERROR : TrayIcon.MessageType.INFO);
        }

        public void remove() {
            try {
                if (icon != null) SystemTray.getSystemTray().remove(icon);
            } catch (Exception ignored) {
            }
        }

        static java.awt.Image iconImage(Color color, String letter) {
            BufferedImage img = new BufferedImage(64, 64, BufferedImage.TYPE_INT_ARGB);
            Graphics2D g = img.createGraphics();
            g.setRenderingHint(java.awt.RenderingHints.KEY_ANTIALIASING,
                    java.awt.RenderingHints.VALUE_ANTIALIAS_ON);
            g.setColor(color);
            g.fillOval(4, 4, 56, 56);
            g.setColor(Color.WHITE);
            g.setFont(new Font("Segoe UI", Font.BOLD, 36));
            g.drawString(letter, 24, 46);
            g.dispose();
            return img;
        }
    }
}
