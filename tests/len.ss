(define length
  (lambda (x)
    (if (null? x)
        0
        (+ 1 (length (cdr x))))))

(define a (quote ()))
(define b (quote (1)))
(define c (quote (1 2)))
(define d (quote (1 2 3)))

(display (length a) "\n")
(display (length b) "\n")
(display (length c) "\n")
(display (length d) "\n")
