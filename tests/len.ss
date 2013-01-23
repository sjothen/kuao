(define length
  (lambda (x)
    (if (null? x)
        0
        (+ 1 (length (cdr x))))))

(define a (quote ()))
(define b (quote (1)))
(define c (quote (1 2)))
(define d (quote (1 2 3)))

(begin
  (display (length a))
  (newline)
  (display (length b))
  (newline)
  (display (length c))
  (newline)
  (display (length d))
  (newline))
