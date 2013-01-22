(define reduce
  (lambda (fn init xs)
    (if (null? xs)
        init
        (fn (car xs) (reduce fn init (cdr xs))))))

(define sum (lambda (xs) (reduce (lambda (x y) (+ x y)) 0 xs)))

(define xs (quote (1 2 3)))
(display (sum xs) "\n")
