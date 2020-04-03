const pynode = require('@fridgerator/pynode')

// Workaround for linking issue in linux:
// https://bugs.python.org/issue4434
// if you get: `undefined symbol: PyExc_ValueError` or `undefined symbol: PyExc_SystemError`
//pynode.dlOpen('libpython3.6m.so') // your libpython shared library

// optionally pass a path to use as Python module search path
pynode.startInterpreter()

// add current path as Python module search path, so it finds our test.py
pynode.appendSysPath('./')

// open the python file (module)
pynode.openFile('testjs')

// call the python function and get a return value
pynode.call('add', 1, 2, (err, result) => {
  if (err) return console.log('error : ', err)
  result === 3 // true
  console.log('success; result = ' + result);
})
