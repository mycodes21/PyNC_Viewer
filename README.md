# PyNC Viewer PRO 🚀

A modern, open-source **G-Code Viewer and Simulator** for CNC machines, written in Python.
Designed for engineers, machinists, and hobbyists who need a fast, lightweight tool to visualize, analyze, and edit G-Code.

![Screenshot](https://via.placeholder.com/800x450?text=PyNC+Viewer+Screenshot)

## ✨ Key Features

- **Real-time Visualization:** 3D OpenGL rendering with Pan/Zoom/Rotate.
- **Animation Mode:** Play/Pause with adjustable speed slider.
- **Smart Scan:** Detects crashes (Rapid into material), missing feeds, and tool errors.
- **Tool Library:** Support for multiple tools (T1, T2...) with custom diameters.
- **DXF Export:** Reverse engineer G-Code back to DXF drawings.
- **Advanced Editor:**
  - Syntax Highlighting.
  - Renumber Lines / Remove Line Numbers.
  - Transformations (Mirror, Scale, Shift, Axis Swap).
- **DRO Panel:** Digital Readout of coordinates during simulation.

## 📦 Installation & Usage

### Option 1: Download EXE (Windows)

Go to the **[Releases](../../releases)** page and download the latest `.exe`. No installation required.

### Option 2: Run from Source

1.  Install Python 3.x
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the app:
    ```bash
    python main.py
    ```

## 🛠 Tech Stack

- **Language:** Python 3.10+
- **GUI:** PySide6 (Qt)
- **Graphics:** PyOpenGL
- **Export:** ezdxf

## 🤝 Contributing

Feel free to fork this repository and submit Pull Requests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Enjoying the tool?** [☕ Buy me a Coffee](https://buymeacoffee.com/mycodes21)
