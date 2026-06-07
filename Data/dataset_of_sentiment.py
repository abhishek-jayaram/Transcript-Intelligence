{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": 4,
   "id": "531a2b8f",
   "metadata": {},
   "outputs": [
    {
     "ename": "KeyError",
     "evalue": "0",
     "output_type": "error",
     "traceback": [
      "\u001b[1;31m---------------------------------------------------------------------------\u001b[0m",
      "\u001b[1;31mKeyError\u001b[0m                                  Traceback (most recent call last)",
      "Cell \u001b[1;32mIn[4], line 6\u001b[0m\n\u001b[0;32m      3\u001b[0m \u001b[38;5;28;01mwith\u001b[39;00m \u001b[38;5;28mopen\u001b[39m(\u001b[38;5;124m\"\u001b[39m\u001b[38;5;124mmaster_meetings.json\u001b[39m\u001b[38;5;124m\"\u001b[39m, \u001b[38;5;124m\"\u001b[39m\u001b[38;5;124mr\u001b[39m\u001b[38;5;124m\"\u001b[39m, encoding\u001b[38;5;241m=\u001b[39m\u001b[38;5;124m\"\u001b[39m\u001b[38;5;124mutf-8\u001b[39m\u001b[38;5;124m\"\u001b[39m) \u001b[38;5;28;01mas\u001b[39;00m f:\n\u001b[0;32m      4\u001b[0m     meetings \u001b[38;5;241m=\u001b[39m json\u001b[38;5;241m.\u001b[39mload(f)\n\u001b[1;32m----> 6\u001b[0m \u001b[38;5;28mprint\u001b[39m(\u001b[43mmeetings\u001b[49m\u001b[43m[\u001b[49m\u001b[38;5;241;43m0\u001b[39;49m\u001b[43m]\u001b[49m\u001b[38;5;241m.\u001b[39mkeys())\n",
      "\u001b[1;31mKeyError\u001b[0m: 0"
     ]
    }
   ],
   "source": [
    "import json\n",
    "\n",
    "with open(\"master_meetings.json\", \"r\", encoding=\"utf-8\") as f:\n",
    "    meetings = json.load(f)\n",
    "\n",
    "print(meetings[0].keys())"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": ".venv (3.10.5)",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.10.5"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
