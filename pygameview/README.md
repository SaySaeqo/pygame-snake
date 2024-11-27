# pygameview - utility library for managing pygame games with multiple views
Pygameview is library that helps managing multiple views created with pygame, helps with using pygame with asyncio for supporting asynchronous operations, brings so common usage menu's views and others handy methods for drawing on screen, like converting strings to pygame's surfaces etc.

# How to use
The simplest workflow assumes you should create PyGameView instance which can overwrite 1 of its 3 methods:
- update(delta) - for most of the operations with delta in seconds in parameters
- handle_event(event) - for handling pygame events (event in parameter)
- do_async() - async function for asynchronous operations

After creating instance of this class it is enough to just await it. View will be running as long as `close_view` or `close_view_with_result` methods will not be called from some place in your code.  
Also you can find some of predifined views in `pygameview.common` module and some usefull functions in `pygameview.utils` module.