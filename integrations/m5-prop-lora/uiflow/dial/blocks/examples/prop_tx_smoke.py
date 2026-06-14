from PropTx import PropTx


proptx_0 = PropTx(13, 15)
colors = proptx_0.default_colors()

proptx_0.preview(proptx_0.first_four(colors))
proptx_0.arm()
proptx_0.stop()
reply = proptx_0.reply()
print(reply)
