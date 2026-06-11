from PropTx import PropTx


proptx_0 = PropTx(13, 15)
colors = proptx_0.default_colors()
colors = proptx_0.set_color(colors, 5, proptx_0.hue_color(60))

proptx_0.preview(proptx_0.first_four(colors))
proptx_0.remote_led3()
proptx_0.remote_led5()
proptx_0.stop()
reply = proptx_0.reply()
print(reply)
