;; simple map function
(define (map f xs)
  (if (null? xs)
      xs
      (cons (f (car xs))
            (map f (cdr xs)))))

(define (println x)
  (display x)
  (display "\n"))

(define xs '(1 2 3 4 5 6 7 8))

(println xs)
(println (map (lambda (x) (+ 1 x)) xs))

; test closure outliving parent
(define (make-adder n)
  (lambda (x) (+ x n)))

(println (map (make-adder 1)
              xs))
