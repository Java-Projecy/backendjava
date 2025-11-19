package com.elecciones.backend.service;

import com.elecciones.backend.model.VotoDistrital;
import com.elecciones.backend.repository.VotoDistritalRepository;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
public class VotoDistritalService {

    private final VotoDistritalRepository repository;

    public VotoDistritalService(VotoDistritalRepository repository) {
        this.repository = repository;
    }

    public List<VotoDistrital> getAll() {
        return repository.findAll();
    }

    public Optional<VotoDistrital> getById(UUID id) {
        return repository.findById(id);
    }

    public VotoDistrital save(VotoDistrital voto) {
        return repository.save(voto);
    }

    public void delete(UUID id) {
        repository.deleteById(id);
    }
}
