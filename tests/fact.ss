(define fact
  (lambda (n)
    (if (= n 0)
      1
      (* n (fact (- n 1))))))

(define fact-tail
  (lambda (n acc)
    (if (= n 0)
        acc
        (fact-tail (- n 1) (* acc n)))))

(display (fact-tail 10 1))
(newline)
(display (fact-tail 1000 1))
(newline)
