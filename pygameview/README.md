# pygameview - utility library for managing pygame games with multiple views
Pygameview is library that helps managing multiple views created with pygame, helps with using pygame with asyncio for supporting asynchronous operations. It brings also common usage menu's views and others handy methods for drawing on screen, like converting strings to pygame's surfaces etc.

# How to use
The simplest workflow assumes you should create PyGameView instance which will overwrite at least 1 of its 3 methods:
- update(delta) - for most of the operations; with delta in seconds as parameter
- handle_event(event) - for handling pygame events
- do_async() - async function for all asynchronous operations

After creating instance of this class it is enough to just await it. View will be running until `close_view` or `close_view_with_result` methods are called. Only 1 view can run at the same time.  
Also you can find some of the predifined views in `pygameview.common` module and some usefull functions in `pygameview.utils` module.