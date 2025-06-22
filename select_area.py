import tkinter as tk
from screeninfo import get_monitors  # pip install screeninfo


def select_screen_area(callback):
    monitor = get_monitors()[0]
    screen_width = monitor.width
    screen_height = monitor.height

    root = tk.Tk()
    root.overrideredirect(True)  # 타이틀바 제거 (완전 화면)
    root.attributes('-topmost', True)  # 항상 위에
    root.attributes('-alpha', 0.3)  # 투명도
    root.geometry(f"{screen_width}x{screen_height}+0+0")
    root.configure(bg='black')

    def disable_close():
        print("⚠️ 반드시 화면 영역 선택 필요")

    root.protocol("WM_DELETE_WINDOW", disable_close)

    canvas = tk.Canvas(root, cursor="cross", bg='black')
    canvas.pack(fill=tk.BOTH, expand=True)

    start_x = start_y = 0
    rect = None
    coord_text = None

    def on_mouse_down(event):
        nonlocal start_x, start_y, rect, coord_text
        start_x = canvas.winfo_pointerx() - canvas.winfo_rootx()
        start_y = canvas.winfo_pointery() - canvas.winfo_rooty()
        rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='red', width=2)
        coord_text = canvas.create_text(start_x, start_y - 20, text="", fill="white", font=("Arial", 12))

    def on_mouse_drag(event):
        cur_x = canvas.winfo_pointerx() - canvas.winfo_rootx()
        cur_y = canvas.winfo_pointery() - canvas.winfo_rooty()
        canvas.coords(rect, start_x, start_y, cur_x, cur_y)
        w = abs(cur_x - start_x)
        h = abs(cur_y - start_y)
        canvas.coords(coord_text, cur_x, cur_y - 20)
        canvas.itemconfig(coord_text, text=f"{w}x{h}")

    def on_mouse_up(event):
        end_x = canvas.winfo_pointerx() - canvas.winfo_rootx()
        end_y = canvas.winfo_pointery() - canvas.winfo_rooty()
        region = (min(start_x, end_x), min(start_y, end_y),
                  abs(start_x - end_x), abs(start_y - end_y))
        print(f"📐 선택된 영역: {region}")
        root.destroy()
        callback(region)

    canvas.bind("<Button-1>", on_mouse_down)
    canvas.bind("<B1-Motion>", on_mouse_drag)
    canvas.bind("<ButtonRelease-1>", on_mouse_up)

    root.mainloop()
