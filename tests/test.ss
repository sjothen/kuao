(define make-adder
  (lambda (init)
    (lambda (x)
      (set! init (+ x init))
      init)))

(define adder (make-adder 0))

(display (adder 10) "\n")
